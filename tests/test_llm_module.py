from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from sdk_test_agent.llm import (
    FakeLlmClient,
    LlmApiProtocol,
    LlmJsonResponseParser,
    LlmMessage,
    LlmModelConfig,
    LlmProviderConfig,
    LlmProviderType,
    LlmRequest,
    LlmResponse,
    LlmResponseFormatType,
    ModelRegistry,
    OpenAICompatibleLlmClient,
)
from sdk_test_agent.llm.llm_errors import LlmCapabilityError, LlmModelNotFoundError, LlmProviderNotFoundError, LlmResponseParseError


def test_fake_llm_client_records_requests_and_returns_content() -> None:
    client = FakeLlmClient(response_content='{"ok": true}')
    request = LlmRequest(model="fake-model", messages=[LlmMessage(role="user", content="hello")])

    response = client.complete(request)

    assert response.content == '{"ok": true}'
    assert response.provider_type == LlmProviderType.FAKE
    assert client.requests == [request]


def test_llm_json_response_parser_cases() -> None:
    parser = LlmJsonResponseParser()
    assert parser.parse_json_object(LlmResponse(content='{"x": 1}')) == {"x": 1}
    assert parser.parse_json_object(LlmResponse(content="", parsed_json={"cached": True})) == {"cached": True}

    with pytest.raises(LlmResponseParseError):
        parser.parse_json_object(LlmResponse(content="[]"))

    with pytest.raises(LlmResponseParseError):
        parser.parse_json_object(LlmResponse(content="not-json"))


def test_model_registry_resolve_and_missing_errors() -> None:
    registry = ModelRegistry()
    registry.register_provider(
        LlmProviderConfig(provider_name="openai_main", provider_type=LlmProviderType.OPENAI, base_url="https://api.example/v1")
    )
    registry.register_model(
        LlmModelConfig(
            alias="planner-default",
            provider_name="openai_main",
            model="gpt-test",
            api_protocol=LlmApiProtocol.RESPONSES,
            max_output_tokens=100,
            supports_structured_output=True,
        )
    )

    resolved = registry.resolve("planner-default")
    assert resolved.model == "gpt-test"
    assert resolved.provider_config.provider_name == "openai_main"
    assert resolved.request_defaults["max_output_tokens"] == 100

    with pytest.raises(LlmModelNotFoundError):
        registry.resolve("missing")

    registry.register_model(LlmModelConfig(alias="bad", provider_name="missing-provider", model="m"))
    with pytest.raises(LlmProviderNotFoundError):
        registry.resolve("bad")


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_1",
            output_text='{"plan": true}',
            status="completed",
            usage={"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
        )


class FakeChatCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        msg = SimpleNamespace(content='{"chat": true}')
        choice = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(id="chat_1", choices=[choice], usage={"prompt_tokens": 2, "completion_tokens": 5, "total_tokens": 7})


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()
        self.chat = SimpleNamespace(completions=FakeChatCompletions())


def test_openai_compatible_responses_request_mapping() -> None:
    fake_client = FakeOpenAIClient()
    registry = ModelRegistry()
    registry.register_provider(LlmProviderConfig(provider_name="p", provider_type=LlmProviderType.OPENAI, base_url="https://api.example/v1"))
    registry.register_model(
        LlmModelConfig(
            alias="planner",
            provider_name="p",
            model="gpt-test",
            api_protocol=LlmApiProtocol.RESPONSES,
            supports_structured_output=True,
        )
    )
    client = OpenAICompatibleLlmClient(
        registry.get_provider("p"),
        model_registry=registry,
        client_factory=lambda **kwargs: fake_client,
    )

    response = client.complete(
        LlmRequest(
            model_alias="planner",
            instructions="system",
            messages=[LlmMessage(role="user", content="make plan")],
            response_format=LlmResponseFormatType.JSON_SCHEMA,
            json_schema={"type": "object"},
            strict_json_schema=True,
            max_output_tokens=123,
        )
    )

    kwargs = fake_client.responses.kwargs
    assert response.content == '{"plan": true}'
    assert kwargs["model"] == "gpt-test"
    assert kwargs["instructions"] == "system"
    assert kwargs["input"][0]["content"][0] == {"type": "input_text", "text": "make plan"}
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["max_output_tokens"] == 123


def test_openai_compatible_chat_request_mapping() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAICompatibleLlmClient(
        LlmProviderConfig(provider_name="p", provider_type=LlmProviderType.OPENAI_COMPATIBLE),
        client_factory=lambda **kwargs: fake_client,
    )

    response = client.complete(
        LlmRequest(
            model="local-model",
            api_protocol=LlmApiProtocol.CHAT_COMPLETIONS,
            instructions="system",
            messages=[LlmMessage(role="user", content="hello")],
            response_format=LlmResponseFormatType.JSON_OBJECT,
        )
    )

    kwargs = fake_client.chat.completions.kwargs
    assert response.content == '{"chat": true}'
    assert kwargs["model"] == "local-model"
    assert kwargs["messages"][0] == {"role": "system", "content": "system"}
    assert kwargs["response_format"] == {"type": "json_object"}


def test_openai_compatible_structured_output_capability_error() -> None:
    fake_client = FakeOpenAIClient()
    registry = ModelRegistry()
    registry.register_provider(LlmProviderConfig(provider_name="p", provider_type=LlmProviderType.OPENAI))
    registry.register_model(LlmModelConfig(alias="weak", provider_name="p", model="weak", supports_structured_output=False))
    client = OpenAICompatibleLlmClient(registry.get_provider("p"), registry, client_factory=lambda **kwargs: fake_client)

    with pytest.raises(LlmCapabilityError):
        client.complete(LlmRequest(model_alias="weak", response_format=LlmResponseFormatType.JSON_OBJECT))
