"""DeepSeek integration and an explicitly labelled local connectivity mock."""

import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_deepseek import ChatDeepSeek

from memorypilot.config import ConfigurationError, Settings


class DeepSeekV4Chat(ChatDeepSeek):
    """Preserve DeepSeek V4 reasoning fields that the upstream serializer drops."""

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        original = self._convert_input(input_).to_messages()
        if len(original) != len(payload["messages"]):
            raise ValueError("模型消息转换前后长度不一致，无法安全保留协议字段。")
        for source, target in zip(original, payload["messages"], strict=True):
            if isinstance(source, AIMessage):
                reasoning = source.additional_kwargs.get("reasoning_content")
                if reasoning is not None:
                    target["reasoning_content"] = reasoning
        return payload


def create_model(settings: Settings, **client_options) -> BaseChatModel:
    if settings.provider == "mock":
        return MockChatModel()
    if not settings.api_key.get_secret_value().strip():
        raise ConfigurationError(
            "尚未配置 DEEPSEEK_API_KEY。请在项目 .env 中填写密钥；离线体验使用 ./run.sh demo。"
        )
    options = dict(
        model=settings.model,
        api_key=settings.api_key,
        api_base=settings.base_url,
        timeout=settings.timeout,
        max_retries=1,
        max_tokens=settings.max_output_tokens,
        extra_body={"thinking": {"type": "enabled" if settings.thinking else "disabled"}},
    )
    if not settings.thinking:
        options["temperature"] = 0
    options.update(client_options)
    return DeepSeekV4Chat(**options)


class MockChatModel(BaseChatModel):
    """Return deterministic fixture responses, never benchmark-quality model answers."""

    @property
    def _llm_type(self) -> str:
        return "memorypilot-offline-mock"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs) -> Any:
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        last_user = max(
            (i for i, msg in enumerate(messages) if isinstance(msg, HumanMessage)), default=-1
        )
        question = str(messages[last_user].content) if last_user >= 0 else ""
        system = "\n".join(str(msg.content) for msg in messages if msg.type == "system")
        current = system.split("CURRENT_FACTS:\n")[-1].split("\nEVIDENCE:")[0]
        tool_results = [msg for msg in messages[last_user + 1 :] if isinstance(msg, ToolMessage)]
        if tool_results:
            data = json.loads(str(tool_results[-1].content))
            answer = "[离线模拟] 查询到的测试酒店：\n" + json.dumps(data, ensure_ascii=False)
        elif any(word in question for word in ["推荐酒店", "查酒店", "找酒店"]):
            match = re.search(r"住宿每晚预算=(\d+(?:\.\d+)?)", current)
            city = "杭州"
            tool_call = {
                "id": "mock_accommodation",
                "name": "search_accommodation",
                "args": {"city": city, "max_price": float(match.group(1)) if match else 500},
                "type": "tool_call",
            }
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[tool_call]))]
            )
        elif any(word in question for word in ["最初", "历史", "之前"]):
            answer = "[离线模拟] 目前保留的要求及来源：\n" + system.split("CURRENT_FACTS:\n")[-1]
        else:
            answer = "[离线模拟] 当前已记录的要求：\n" + current
        message = AIMessage(
            content=answer,
            usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        return ChatResult(generations=[ChatGeneration(message=message)])
