"""Local-only HTTP interface; model requests remain explicit."""

from threading import Lock

from fastapi import FastAPI, HTTPException

from memorypilot.config import ConfigurationError, Settings
from memorypilot.schemas import ChatRequest, ChatResult, Scope
from memorypilot.service import MemoryPilot


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    application = FastAPI(title="MemoryPilot", version="0.1.0")
    service = MemoryPilot(config)
    lock = Lock()

    @application.get("/health")
    def health():
        return {
            "status": "ok",
            "provider": config.provider,
            "model": config.model,
            "api_key_configured": bool(config.api_key.get_secret_value().strip()),
        }

    @application.post("/chat", response_model=ChatResult)
    def chat(request: ChatRequest):
        with lock:
            try:
                return service.chat(request)
            except ConfigurationError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from None
            except ValueError:
                raise HTTPException(status_code=422, detail="输入或上下文无法处理。") from None
            except Exception:
                raise HTTPException(
                    status_code=502, detail="模型或工具执行失败，请检查本地配置。"
                ) from None

    @application.get("/memories")
    def memories(
        user: str = "demo",
        trip: str = "hangzhou",
        namespace: str = "default",
        history: bool = False,
    ):
        try:
            scope = Scope(user_id=user, trip_id=trip, namespace=namespace)
        except ValueError:
            raise HTTPException(status_code=422, detail="用户、旅行或实验范围无效。") from None
        return service.repository.facts(scope, history=history)

    return application


app = create_app()
