from fastapi.testclient import TestClient

from memorypilot.api import create_app
from memorypilot.config import Settings
from memorypilot.evaluation import run_smoke


def test_http_health_memory_and_chat(tmp_path):
    config = Settings(_env_file=None, provider="mock", data_dir=tmp_path)
    with TestClient(create_app(config)) as client:
        assert client.get("/health").json()["provider"] == "mock"
        result = client.post("/chat", json={"message": "住宿预算每晚500元。"})
        assert result.status_code == 200
        assert result.json()["facts"][0]["value"] == "500"
        assert client.get("/memories").json()[0]["value"] == "500"


def test_missing_key_is_explicit_and_never_falls_back(tmp_path):
    config = Settings(_env_file=None, provider="deepseek", api_key="", data_dir=tmp_path)
    with TestClient(create_app(config)) as client:
        assert client.get("/health").status_code == 200
        result = client.post("/chat", json={"message": "hello"})
        assert result.status_code == 503
        assert "DEEPSEEK_API_KEY" in result.json()["detail"]


def test_smoke_suite_counts_every_case_and_marks_mock(tmp_path):
    config = Settings(_env_file=None, provider="mock", data_dir=tmp_path / "db")
    summary = run_smoke(config, tmp_path / "result")
    assert summary["total"] == summary["passed"] == 3
    assert summary["scientific_benchmark"] is False
    assert len((tmp_path / "result" / "predictions.jsonl").read_text().splitlines()) == 3
