"""Keep the template's model helper while selecting DeepSeek explicitly."""

from langchain_core.messages import BaseMessage

from memorypilot.config import Settings
from memorypilot.providers import create_model


def get_message_text(msg: BaseMessage) -> str:
    return msg.content if isinstance(msg.content, str) else str(msg.content)


def load_chat_model(fully_specified_name: str):
    provider, model = fully_specified_name.split("/", maxsplit=1)
    if provider != "deepseek":
        raise ValueError("当前仅配置 DeepSeek；离线模式通过 MEMORYPILOT_PROVIDER=mock 选择。")
    return create_model(Settings(model=model))
