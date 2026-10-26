import json

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from memorypilot.config import ConfigurationError, Settings
from memorypilot.extraction import LangMemExtractor
from memorypilot.providers import create_model


@tool
def echo(text: str) -> str:
    """Echo text for an offline protocol test."""
    return text


def settings(**kwargs):
    return Settings(_env_file=None, api_key="fixture-key-not-a-real-secret", **kwargs)


def response(message, finish="stop"):
    return {
        "id": "chatcmpl-fixture",
        "object": "chat.completion",
        "created": 1,
        "model": "deepseek-v4-pro",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def test_default_model_and_key_error(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = Settings(_env_file=None, api_key="")
    assert config.model == "deepseek-v4-pro"
    with pytest.raises(ConfigurationError):
        create_model(config)


def test_real_client_payload_uses_deepseek_and_disables_thinking():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        return httpx.Response(200, json=response({"role": "assistant", "content": "fixture ok"}))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    model = create_model(settings(), http_client=client, max_retries=0)
    result = model.invoke([HumanMessage(content="hello")])
    assert result.content == "fixture ok"
    assert seen[0]["model"] == "deepseek-v4-pro"
    assert seen[0]["thinking"] == {"type": "disabled"}


def test_thinking_tool_protocol_retains_reasoning_for_all_assistant_messages():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response(
                {
                    "role": "assistant",
                    "content": "done",
                    "reasoning_content": "protocol fixture only",
                }
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    model = create_model(settings(thinking=True), http_client=client, max_retries=0).bind_tools(
        [echo]
    )
    model.invoke(
        [
            HumanMessage(content="first"),
            AIMessage(
                content="previous answer",
                additional_kwargs={"reasoning_content": "previous fixture"},
            ),
            HumanMessage(content="second"),
            AIMessage(
                content="",
                additional_kwargs={"reasoning_content": "call fixture"},
                tool_calls=[
                    {"name": "echo", "args": {"text": "hello"}, "id": "call1", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="hello", tool_call_id="call1"),
        ]
    )
    assistants = [item for item in seen[0]["messages"] if item["role"] == "assistant"]
    assert [item.get("reasoning_content") for item in assistants] == [
        "previous fixture",
        "call fixture",
    ]
    assert seen[0]["thinking"] == {"type": "enabled"}


def test_langmem_extraction_uses_schema_with_fake_http_not_custom_regex():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "extract1",
                            "type": "function",
                            "function": {
                                "name": "CandidateFact",
                                "arguments": json.dumps(
                                    {
                                        "attribute": "accommodation_budget_per_night",
                                        "value": "700",
                                        "quote": "700",
                                    }
                                ),
                            },
                        }
                    ],
                },
                finish="tool_calls",
            ),
        )

    model = create_model(
        settings(), http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0
    )
    facts = LangMemExtractor(model).extract("我的住宿预算每晚700元。")
    assert facts[0].value == "700"
    assert any(tool["function"]["name"] == "CandidateFact" for tool in seen[0]["tools"])
