"""Small pipeline checks and a label-safe LongMemEval input adapter."""

import json
from pathlib import Path

from memorypilot.config import Settings
from memorypilot.schemas import ChatRequest, Scope
from memorypilot.service import MemoryPilot


def split_longmemeval(sample: dict) -> tuple[list[dict], dict, dict]:
    """Keep grading labels and the future question away from history ingestion."""
    required = ["question_id", "question", "question_date", "haystack_sessions", "haystack_dates"]
    if any(key not in sample for key in required):
        raise ValueError("LongMemEval 样本缺少必要字段。")
    if len(sample["haystack_sessions"]) != len(sample["haystack_dates"]):
        raise ValueError("会话数量与时间数量不一致。")
    sessions = []
    for date, turns in zip(sample["haystack_dates"], sample["haystack_sessions"], strict=True):
        sessions.append(
            {
                "date": date,
                "messages": [{"role": item["role"], "content": item["content"]} for item in turns],
            }
        )
    query = {
        "question_id": sample["question_id"],
        "question": sample["question"],
        "question_date": sample["question_date"],
    }
    grading = {
        key: sample.get(key)
        for key in ["question_id", "question_type", "answer", "answer_session_ids"]
    }
    return sessions, query, grading


def run_smoke(settings: Settings, output: Path) -> dict:
    """Test application plumbing with fixtures, not scientific model performance."""
    if settings.provider != "mock":
        raise ValueError("该命令只运行离线流程检查；正式模型评测尚未实现。")
    app = MemoryPilot(settings)
    # Each evaluation gets fresh scope; repeated runs never read earlier results.
    from uuid import uuid4

    scope = Scope(user_id="smoke", trip_id="hangzhou", namespace=f"smoke-{uuid4().hex}")
    cases = [
        ("s1", "我的住宿预算每晚500元，不吃海鲜。", "500"),
        ("s2", "我的住宿预算改为每晚700元。", "700"),
        ("s3", "请推荐酒店。", "示例西湖客栈"),
    ]
    rows = []
    for session, message, expected in cases:
        try:
            result = app.chat(ChatRequest(scope=scope, session_id=session, message=message))
            rows.append(
                {
                    "question_id": session,
                    "hypothesis": result.answer,
                    "passed": expected in result.answer,
                    "provider": "mock",
                    "run_id": result.run_id,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "question_id": session,
                    "hypothesis": "",
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "provider": "mock",
                }
            )
    output.mkdir(parents=True, exist_ok=True)
    (output / "predictions.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8"
    )
    summary = {
        "kind": "offline_pipeline_smoke",
        "provider": "mock",
        "total": len(cases),
        "passed": sum(row["passed"] for row in rows),
        "scientific_benchmark": False,
        "note": "仅验证离线流程，不代表 DeepSeek、长期记忆基准或规划质量。",
    }
    (output / "metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
