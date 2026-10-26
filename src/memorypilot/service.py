"""Combine memory ingestion, bounded context, LangGraph, and sanitized traces."""

import hashlib
import json
import time
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from memorypilot.config import Settings
from memorypilot.context_builder import build_context
from memorypilot.extraction import LangMemExtractor, MockExtractor
from memorypilot.providers import create_model
from memorypilot.repository import Repository
from memorypilot.schemas import ChatRequest, ChatResult
from memorypilot.tools import make_tools
from react_agent.graph import build_graph


class MemoryPilot:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.data_dir = self.settings.resolved_data_dir
        self.repository = Repository(self.data_dir / "memory.sqlite3")

    def chat(self, request: ChatRequest) -> ChatResult:
        start = time.monotonic()
        run_id = f"run_{uuid4().hex}"
        # Fail clearly before persisting user input when the configured provider lacks a key.
        model = create_model(self.settings)
        # LangMem may force a schema tool; DeepSeek thinking mode only supports auto tools.
        extractor = (
            MockExtractor()
            if self.settings.provider == "mock"
            else LangMemExtractor(
                create_model(self.settings.model_copy(update={"thinking": False}))
            )
        )
        source_id = self.repository.add_event(request.scope, request.session_id, request.message)
        try:
            candidates = extractor.extract(request.message)
            self.repository.write_facts(request.scope, source_id, candidates)
            facts = self.repository.facts(request.scope)
            tools = make_tools(self.repository, request.scope)
            context = build_context(
                request.message,
                facts,
                self.repository.recent_events(request.scope),
                tools,
                self.settings.context_budget,
            )
            thread_id = hashlib.sha256(
                json.dumps(
                    [request.scope.model_dump(), request.session_id], sort_keys=True
                ).encode()
            ).hexdigest()
            with SqliteSaver.from_conn_string(str(self.data_dir / "checkpoints.sqlite3")) as saver:
                graph = build_graph(model, tools, self.settings, saver)
                output = graph.invoke(
                    {
                        "messages": context.messages,
                        "model_calls": 0,
                        "tool_calls": 0,
                        "deadline": start + self.settings.task_timeout,
                        "usage": [],
                    },
                    config={"configurable": {"thread_id": thread_id}, "recursion_limit": 30},
                )
            answer = str(output["messages"][-1].content)
            tool_names = []
            # Limit trace collection to this request rather than recounting earlier turns.
            last_user = max(i for i, msg in enumerate(output["messages"]) if msg.type == "human")
            for message in output["messages"][last_user + 1 :]:
                tool_names.extend(call["name"] for call in getattr(message, "tool_calls", []))
            result = ChatResult(
                run_id=run_id,
                answer=answer,
                provider=self.settings.provider,
                model=self.settings.model
                if self.settings.provider == "deepseek"
                else "offline-fixture",
                facts=facts,
                evidence_ids=context.selected_ids,
                model_calls=output["model_calls"],
                tool_names=tool_names,
                usage=output["usage"],
                context_units=context.units,
                elapsed_seconds=round(time.monotonic() - start, 3),
            )
            self.repository.add_event(request.scope, request.session_id, answer, role="assistant")
            # Export only known safe fields; never serialize model clients, keys, or reasoning.
            trace = {
                "run_id": run_id,
                "provider": result.provider,
                "model": result.model,
                "scope": request.scope.model_dump(),
                "session_id": request.session_id,
                "model_calls": result.model_calls,
                "tool_names": tool_names,
                "evidence_ids": result.evidence_ids,
                "dropped_ids": context.dropped_ids,
                "context_estimate_bytes": context.units,
                "usage": result.usage,
                "elapsed_seconds": result.elapsed_seconds,
                "status": "completed",
                "extractor_calls": 0 if self.settings.provider == "mock" else 1,
                "extractor_usage": "not_instrumented",
            }
            self.repository.save_run(run_id, trace)
            traces = self.data_dir / "traces"
            traces.mkdir(parents=True, exist_ok=True)
            (traces / f"{run_id}.json").write_text(
                json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return result
        except Exception as exc:
            self.repository.save_run(
                run_id,
                {
                    "run_id": run_id,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "scope": request.scope.model_dump(),
                },
            )
            raise
