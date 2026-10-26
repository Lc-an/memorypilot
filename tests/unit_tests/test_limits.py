import time

import pytest
from langchain_core.messages import HumanMessage

from memorypilot.config import Settings
from memorypilot.context_builder import build_context
from memorypilot.providers import MockChatModel
from memorypilot.repository import Repository
from memorypilot.schemas import Scope
from memorypilot.tools import make_tools
from react_agent.graph import AgentLimitError, build_graph


def test_model_call_limit_stops_an_unfinished_tool_loop(tmp_path):
    settings = Settings(_env_file=None, provider="mock", max_model_calls=1)
    tools = make_tools(Repository(tmp_path / "m.sqlite3"), Scope(user_id="a", trip_id="t"))
    context = build_context("请推荐酒店。", [], [], tools, settings.context_budget)
    graph = build_graph(MockChatModel(), tools, settings)
    with pytest.raises(AgentLimitError, match="模型调用次数"):
        graph.invoke({"messages": context.messages})


def test_expired_deadline_prevents_any_model_call():
    settings = Settings(_env_file=None, provider="mock")
    graph = build_graph(MockChatModel(), [], settings)
    with pytest.raises(AgentLimitError, match="时间上限"):
        graph.invoke(
            {"messages": [HumanMessage(content="hello")], "deadline": time.monotonic() - 1}
        )
