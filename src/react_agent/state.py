"""Extend the upstream message state with per-request counters."""

from dataclasses import dataclass, field
from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


@dataclass
class InputState:
    messages: Annotated[list[AnyMessage], add_messages] = field(default_factory=list)
    model_calls: int = 0
    tool_calls: int = 0
    deadline: float = 0
    usage: list[dict] = field(default_factory=list)


@dataclass
class State(InputState):
    pass
