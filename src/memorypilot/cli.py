"""Command-line entry points for setup verification and local development."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from memorypilot.config import ConfigurationError, Settings
from memorypilot.evaluation import run_smoke
from memorypilot.schemas import ChatRequest, Scope
from memorypilot.service import MemoryPilot


def dump(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def scoped(parser):
    parser.add_argument("--user", default="demo")
    parser.add_argument("--trip", default="hangzhou")
    parser.add_argument("--namespace", default="default")


def main() -> int:
    parser = argparse.ArgumentParser(description="MemoryPilot：多会话记忆 Agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="检查环境，不调用生成模型")
    commands.add_parser("demo", help="临时数据库离线演示，不使用 API 密钥")
    chat = commands.add_parser("chat", help="发送一条消息；默认调用 DeepSeek")
    chat.add_argument("message")
    chat.add_argument("--provider", choices=["mock", "deepseek"])
    chat.add_argument("--session", default="session-1")
    scoped(chat)
    memories = commands.add_parser("memories", help="查看当前或历史事实")
    memories.add_argument("--history", action="store_true")
    memories.add_argument("--as-of", help="带时区的 ISO 时间")
    scoped(memories)
    smoke = commands.add_parser("eval-smoke", help="离线评测流程检查")
    smoke.add_argument("--output", type=Path, default=Path("results/smoke"))
    commands.add_parser("serve", help="在 127.0.0.1:8000 启动本地 API")
    args = parser.parse_args()
    settings = Settings()
    if args.command == "doctor":
        dump(
            {
                "python": sys.version.split()[0],
                "provider": settings.provider,
                "model": settings.model,
                "base_url": settings.base_url,
                "api_key_configured": bool(settings.api_key.get_secret_value().strip()),
                "thinking": settings.thinking,
                "database": str(settings.resolved_data_dir),
                "context_estimator": "UTF-8 bytes, not exact tokens",
            }
        )
        return 0
    if args.command == "serve":
        import uvicorn

        uvicorn.run("memorypilot.api:app", host="127.0.0.1", port=8000)
        return 0
    if args.command == "demo":
        with tempfile.TemporaryDirectory(prefix="memorypilot-") as directory:
            local = settings.model_copy(update={"provider": "mock", "data_dir": Path(directory)})
            app = MemoryPilot(local)
            for index, message in enumerate(
                [
                    "我的住宿预算每晚500元，不吃海鲜。",
                    "我的住宿预算改为每晚700元。",
                    "请推荐酒店。",
                    "我最初的预算是多少？",
                ],
                1,
            ):
                result = app.chat(ChatRequest(session_id=f"session-{index}", message=message))
                dump({"session": index, "message": message, "result": result.model_dump()})
        return 0
    if args.command == "eval-smoke":
        local = settings.model_copy(update={"provider": "mock"})
        result = run_smoke(local, args.output)
        dump(result)
        return 0 if result["passed"] == result["total"] else 1
    scope = Scope(user_id=args.user, trip_id=args.trip, namespace=args.namespace)
    if args.command == "memories":
        facts = MemoryPilot(settings).repository.facts(
            scope, history=args.history, as_of=args.as_of
        )
        dump([fact.model_dump() for fact in facts])
        return 0
    if args.provider:
        settings = settings.model_copy(update={"provider": args.provider})
    result = MemoryPilot(settings).chat(
        ChatRequest(scope=scope, session_id=args.session, message=args.message)
    )
    dump(result.model_dump())
    return 0


def entrypoint() -> int:
    try:
        return main()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        # Provider exceptions may contain request data. Print only type, never credentials.
        print(f"执行失败：{type(exc).__name__}。请查看配置或项目测试。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
