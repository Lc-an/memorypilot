import pytest

from memorypilot.context_builder import ContextBudgetError, build_context, message_units
from memorypilot.evaluation import split_longmemeval
from memorypilot.schemas import Evidence, Fact


def test_required_facts_are_retained_and_large_optional_evidence_is_dropped():
    fact = Fact(
        fact_id="f1",
        attribute="diet",
        value="不吃海鲜",
        known_at="2026-10-01T00:00:00+00:00",
        source_id="src1",
    )
    evidence = Evidence(source_id="large", text="很长" * 5000, timestamp=fact.known_at)
    result = build_context("我的要求是什么？", [fact], [evidence], [], 2000)
    assert "不吃海鲜" in result.messages[0].content
    assert result.dropped_ids == ["large"]
    assert result.units <= 2000
    assert result.units == message_units(result.messages, [])


def test_oversized_required_question_is_not_silently_truncated():
    with pytest.raises(ContextBudgetError):
        build_context("必须保留" * 10000, [], [], [], 1000)


def test_longmemeval_ingestion_never_contains_question_or_answer_labels():
    sample = {
        "question_id": "q1",
        "question_type": "knowledge-update",
        "question": "hidden future query",
        "question_date": "2026/10/02",
        "answer": "SECRET ANSWER",
        "answer_session_ids": ["s1"],
        "haystack_dates": ["2026/10/01"],
        "haystack_sessions": [[{"role": "user", "content": "past message", "has_answer": True}]],
    }
    sessions, query, grading = split_longmemeval(sample)
    assert sessions == [
        {"date": "2026/10/01", "messages": [{"role": "user", "content": "past message"}]}
    ]
    assert query["question"] == "hidden future query"
    assert grading["answer"] == "SECRET ANSWER"
    assert "SECRET" not in str(sessions)
    assert "has_answer" not in str(sessions)


def test_bad_dataset_lengths_fail_before_running_models():
    with pytest.raises(ValueError):
        split_longmemeval(
            {
                "question_id": "q",
                "question": "q",
                "question_date": "today",
                "haystack_sessions": [],
                "haystack_dates": ["today"],
            }
        )
