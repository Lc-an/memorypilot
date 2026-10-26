from memorypilot.config import Settings
from memorypilot.schemas import ChatRequest, Scope
from memorypilot.service import MemoryPilot


def local_settings(tmp_path):
    return Settings(_env_file=None, provider="mock", data_dir=tmp_path)


def test_memory_survives_new_service_and_session(tmp_path):
    settings = local_settings(tmp_path)
    scope = Scope(user_id="alice", trip_id="hz")
    app = MemoryPilot(settings)
    first = app.chat(ChatRequest(scope=scope, session_id="one", message="住宿预算每晚500元。"))
    second = MemoryPilot(settings).chat(
        ChatRequest(scope=scope, session_id="two", message="住宿预算改为每晚700元。")
    )
    assert first.facts[0].value == "500"
    assert second.facts[0].value == "700"
    assert second.facts[0].supersedes == first.facts[0].fact_id
    history = MemoryPilot(settings).repository.facts(scope, history=True)
    assert [item.value for item in history] == ["500", "700"]


def test_tool_loop_uses_updated_budget(tmp_path):
    app = MemoryPilot(local_settings(tmp_path))
    app.chat(ChatRequest(session_id="one", message="住宿预算每晚700元。"))
    result = app.chat(ChatRequest(session_id="two", message="请推荐酒店。"))
    assert result.tool_names == ["search_accommodation"]
    assert result.model_calls == 2
    assert "示例西湖客栈" in result.answer


def test_same_session_resets_request_counters_and_replaces_system_context(tmp_path):
    app = MemoryPilot(local_settings(tmp_path))
    app.chat(ChatRequest(message="住宿预算每晚500元。"))
    result = app.chat(ChatRequest(message="住宿预算改为每晚700元。"))
    assert result.model_calls == 1
    assert "住宿每晚预算=700" in result.answer
    assert "住宿每晚预算=500" not in result.answer


def test_traces_do_not_export_protocol_reasoning_or_credentials(tmp_path):
    app = MemoryPilot(local_settings(tmp_path))
    app.chat(ChatRequest(message="住宿预算每晚500元。"))
    content = next((tmp_path / "traces").glob("*.json")).read_text()
    assert "reasoning_content" not in content
    assert "api_key" not in content
    assert '"status": "completed"' in content


def test_namespaces_and_users_are_isolated(tmp_path):
    app = MemoryPilot(local_settings(tmp_path))
    app.chat(ChatRequest(message="住宿预算每晚500元。"))
    result = app.chat(
        ChatRequest(
            scope=Scope(user_id="someone_else", trip_id="hangzhou"),
            message="我的预算是多少？",
        )
    )
    assert result.facts == []
    assert "500" not in result.answer
