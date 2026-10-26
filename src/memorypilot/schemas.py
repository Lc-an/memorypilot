"""Shared contracts for memory, requests, and results."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("时间必须包含时区，例如 +08:00。")
    return parsed.astimezone(UTC).isoformat()


class Scope(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: str = Field(min_length=1, max_length=80)
    trip_id: str = Field(min_length=1, max_length=80)
    namespace: str = Field("default", min_length=1, max_length=80)


class CandidateFact(BaseModel):
    """Propose a fact with an exact supporting quote from the current user message."""

    attribute: Literal["accommodation_budget_per_night", "diet", "destination", "travel_dates"]
    value: str = Field(min_length=1, max_length=400)
    quote: str = Field(min_length=1, max_length=500)


class Fact(BaseModel):
    fact_id: str
    attribute: str
    value: str
    known_at: str
    source_id: str
    supersedes: str | None = None


class Evidence(BaseModel):
    source_id: str
    text: str
    timestamp: str


class ChatRequest(BaseModel):
    scope: Scope = Field(default_factory=lambda: Scope(user_id="demo", trip_id="hangzhou"))
    session_id: str = Field("session-1", min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=12000)


class ChatResult(BaseModel):
    run_id: str
    answer: str
    provider: str
    model: str
    facts: list[Fact]
    evidence_ids: list[str]
    model_calls: int
    tool_names: list[str]
    usage: list[dict]
    context_units: int
    elapsed_seconds: float
