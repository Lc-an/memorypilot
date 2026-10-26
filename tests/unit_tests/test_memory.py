import pytest

from memorypilot.repository import Repository
from memorypilot.schemas import CandidateFact, Scope


def candidate(value, quote=None):
    return CandidateFact(
        attribute="accommodation_budget_per_night", value=value, quote=quote or value
    )


def put(repo, scope, value, day, source_id=None):
    source = repo.add_event(
        scope,
        "s1",
        f"住宿每晚预算{value}元。",
        timestamp=f"2026-10-{day:02d}T09:00:00+08:00",
        source_id=source_id,
    )
    return repo.write_facts(scope, source, [candidate(value)])[0]


def test_history_time_cutoff_and_restart(tmp_path):
    repo = Repository(tmp_path / "m.sqlite3")
    scope = Scope(user_id="a", trip_id="t")
    first = put(repo, scope, "500", 1)
    second = put(repo, scope, "700", 2)
    restarted = Repository(repo.path)
    assert restarted.facts(scope)[0].value == "700"
    assert restarted.facts(scope, as_of="2026-10-01T18:00:00+08:00")[0].value == "500"
    assert second.supersedes == first.fact_id
    assert restarted.facts(scope, as_of="2026-09-01T18:00:00+08:00") == []


def test_scopes_and_source_reads_are_checked(tmp_path):
    repo = Repository(tmp_path / "m.sqlite3")
    scope = Scope(user_id="a", trip_id="t")
    fact = put(repo, scope, "500", 1)
    for other in [
        Scope(user_id="b", trip_id="t"),
        Scope(user_id="a", trip_id="other"),
        Scope(user_id="a", trip_id="t", namespace="experiment2"),
    ]:
        assert repo.facts(other) == []
        assert repo.read_evidence(other, fact.source_id) is None
        with pytest.raises(ValueError):
            repo.write_facts(other, fact.source_id, [candidate("500")])


def test_invalid_quote_or_value_rolls_back(tmp_path):
    repo = Repository(tmp_path / "m.sqlite3")
    scope = Scope(user_id="a", trip_id="t")
    source = repo.add_event(scope, "s", "住宿每晚500元。")
    for item in [candidate("700"), candidate("700", "住宿每晚500元。")]:
        with pytest.raises(ValueError):
            repo.write_facts(scope, source, [item])
        assert repo.facts(scope) == []


def test_repeated_source_and_value_do_not_duplicate_fact_versions(tmp_path):
    repo = Repository(tmp_path / "m.sqlite3")
    scope = Scope(user_id="a", trip_id="t")
    first = put(repo, scope, "500", 1, "source1")
    repeated = put(repo, scope, "500", 1, "source1")
    assert first.fact_id == repeated.fact_id
    assert len(repo.facts(scope, history=True)) == 1


def test_assistant_suggestion_cannot_become_user_fact(tmp_path):
    repo = Repository(tmp_path / "m.sqlite3")
    scope = Scope(user_id="a", trip_id="t")
    source = repo.add_event(scope, "s", "建议预算500元", role="assistant")
    with pytest.raises(ValueError):
        repo.write_facts(scope, source, [candidate("500")])


def test_out_of_order_input_does_not_replace_newer_current_value(tmp_path):
    repo = Repository(tmp_path / "m.sqlite3")
    scope = Scope(user_id="a", trip_id="t")
    put(repo, scope, "700", 2)
    put(repo, scope, "500", 1)
    assert repo.facts(scope)[0].value == "700"
