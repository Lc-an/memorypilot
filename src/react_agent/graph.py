"""Adapt the MIT LangGraph ReAct template's model/tool loop for MemoryPilot."""

import time

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from memorypilot.config import Settings
from memorypilot.context_builder import ContextBudgetError, message_units
from memorypilot.providers import create_model
from react_agent.state import InputState, State


class AgentLimitError(RuntimeError):
    pass


def build_graph(model=None, tools=None, settings: Settings | None = None, checkpointer=None):
    settings = settings or Settings()
    tools = tools or []
    bound_model = model.bind_tools(tools) if model is not None else None

    def call_model(state: State):
        remaining = state.deadline - time.monotonic() if state.deadline else settings.task_timeout
        if remaining <= 0:
            raise AgentLimitError("已到本次任务时间上限。")
        if state.model_calls >= settings.max_model_calls:
            raise AgentLimitError("已到本次模型调用次数上限，任务没有完成。")
        if message_units(list(state.messages), tools) > settings.context_budget:
            raise ContextBudgetError("工具结果或会话历史超过预算，已停止本次任务。")
        active_model = bound_model or create_model(settings).bind_tools(tools)
        response = active_model.invoke(state.messages, timeout=min(settings.timeout, remaining))
        if not isinstance(response, AIMessage):
            raise TypeError("生成模型返回了不支持的消息类型。")
        if response.response_metadata.get("finish_reason") in {"length", "content_filter"}:
            raise AgentLimitError("模型输出被截断或中止，未把不完整结果标记为成功。")
        if state.tool_calls + len(response.tool_calls) > settings.max_tool_calls:
            raise AgentLimitError("已到本次工具调用次数上限。")
        if state.deadline and time.monotonic() >= state.deadline:
            raise AgentLimitError("模型返回时已经超出任务时间上限。")
        usage = [*state.usage]
        if response.usage_metadata:
            usage.append(dict(response.usage_metadata))
        # Protocol reasoning remains in graph messages, never in exported trace payloads.
        return {
            "messages": [response],
            "model_calls": state.model_calls + 1,
            "tool_calls": state.tool_calls + len(response.tool_calls),
            "usage": usage,
        }

    def route_model_output(state: State):
        last_message = state.messages[-1]
        if not isinstance(last_message, AIMessage):
            raise ValueError("最后一条消息应当由模型生成。")
        return "tools" if last_message.tool_calls else END

    builder = StateGraph(State, input_schema=InputState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", route_model_output)
    builder.add_edge("tools", "call_model")
    return builder.compile(checkpointer=checkpointer, name="MemoryPilot")


# Keep the upstream graph export importable. The CLI/API service binds scoped tools and memory.
graph = build_graph()
