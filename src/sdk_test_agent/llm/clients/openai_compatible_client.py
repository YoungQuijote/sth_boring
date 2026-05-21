from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from typing import Any, Callable

from sdk_test_agent.llm.llm_config import LlmProviderConfig
from sdk_test_agent.llm.llm_enums import LlmApiProtocol, LlmProviderType, LlmResponseFormatType
from sdk_test_agent.llm.llm_errors import LlmCapabilityError, LlmConfigError, LlmProviderError
from sdk_test_agent.llm.llm_models import LlmContentPart, LlmMessage, LlmRequest, LlmResponse
from sdk_test_agent.llm.model_registry import ModelRegistry, ResolvedLlmTarget
from sdk_test_agent.llm.streaming.stream_models import LlmStreamEvent
from sdk_test_agent.llm.usage import LlmUsage


class OpenAICompatibleLlmClient:
    def __init__(
        self,
        provider_config: LlmProviderConfig,
        model_registry: ModelRegistry | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.provider_config = provider_config
        self.model_registry = model_registry
        self._client_factory = client_factory
        self._client: Any | None = None

    def complete(self, request: LlmRequest) -> LlmResponse:
        start = time.monotonic()
        resolved = self._resolve(request)
        protocol = request.api_protocol or resolved.api_protocol
        try:
            if protocol == LlmApiProtocol.RESPONSES:
                response = self._complete_responses(request, resolved)
            elif protocol == LlmApiProtocol.CHAT_COMPLETIONS:
                response = self._complete_chat_completions(request, resolved)
            else:
                raise LlmConfigError(f"unsupported api_protocol: {protocol}")
        except (LlmCapabilityError, LlmConfigError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise LlmProviderError(str(exc)) from exc
        response.latency_ms = int((time.monotonic() - start) * 1000)
        return response

    async def acomplete(self, request: LlmRequest) -> LlmResponse:
        raise NotImplementedError("OpenAICompatibleLlmClient.acomplete is reserved for a future async adapter")

    async def astream(self, request: LlmRequest) -> AsyncIterator[LlmStreamEvent]:
        raise NotImplementedError("OpenAICompatibleLlmClient.astream is reserved for a future streaming adapter")
        yield  # pragma: no cover

    def _resolve(self, request: LlmRequest) -> ResolvedLlmTarget:
        if request.model_alias and self.model_registry is not None:
            return self.model_registry.resolve(request.model_alias)
        model = request.model
        if not model:
            raise LlmConfigError("request must include model or resolvable model_alias")
        return ResolvedLlmTarget(
            provider_config=self.provider_config,
            model_config=_ad_hoc_model_config(model, self.provider_config.provider_name),
            model=model,
            api_protocol=request.api_protocol or LlmApiProtocol.RESPONSES,
            request_defaults={},
        )

    def _complete_responses(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> LlmResponse:
        self._validate_structured_output(request, resolved)
        kwargs = self._build_responses_kwargs(request, resolved)
        raw = self._get_client().responses.create(**kwargs)
        return self._normalize_responses(raw, request, resolved)

    def _complete_chat_completions(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> LlmResponse:
        self._validate_structured_output(request, resolved)
        kwargs = self._build_chat_kwargs(request, resolved)
        raw = self._get_client().chat.completions.create(**kwargs)
        return self._normalize_chat(raw, request, resolved)

    def _build_responses_kwargs(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> dict[str, Any]:
        kwargs = {
            "model": resolved.model,
            "input": [self._message_to_responses_input(m) for m in request.messages],
            "metadata": request.metadata or None,
        }
        if request.instructions:
            kwargs["instructions"] = request.instructions
        if request.tools:
            kwargs["tools"] = request.tools
        if request.tool_choice is not None:
            kwargs["tool_choice"] = request.tool_choice
        max_tokens = request.max_output_tokens or resolved.request_defaults.get("max_output_tokens")
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        reasoning = request.reasoning_effort or resolved.request_defaults.get("reasoning_effort")
        if reasoning:
            kwargs["reasoning"] = {"effort": reasoning}
        text = self._responses_text_format(request, resolved)
        if text:
            kwargs["text"] = text
        kwargs.update(request.extra_body)
        return {k: v for k, v in kwargs.items() if v is not None}

    def _build_chat_kwargs(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> dict[str, Any]:
        messages = []
        if request.instructions:
            messages.append({"role": "system", "content": request.instructions})
        messages.extend(self._message_to_chat(m) for m in request.messages)
        kwargs = {
            "model": resolved.model,
            "messages": messages,
            "temperature": request.temperature if request.temperature is not None else resolved.request_defaults.get("temperature"),
            "top_p": request.top_p if request.top_p is not None else resolved.request_defaults.get("top_p"),
            "max_tokens": request.max_output_tokens or resolved.request_defaults.get("max_output_tokens"),
            "stream": False,
        }
        response_format = self._chat_response_format(request, resolved)
        if response_format:
            kwargs["response_format"] = response_format
        if request.tools:
            kwargs["tools"] = request.tools
        if request.tool_choice is not None:
            kwargs["tool_choice"] = request.tool_choice
        kwargs.update(request.extra_body)
        return {k: v for k, v in kwargs.items() if v is not None}

    def _responses_text_format(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> dict[str, Any] | None:
        fmt = request.response_format or resolved.request_defaults.get("response_format")
        schema = request.json_schema or resolved.request_defaults.get("json_schema")
        strict = request.strict_json_schema or bool(resolved.request_defaults.get("strict_json_schema"))
        if fmt == LlmResponseFormatType.JSON_SCHEMA:
            return {"format": {"type": "json_schema", "name": "structured_output", "schema": schema or {}, "strict": strict}}
        if fmt == LlmResponseFormatType.JSON_OBJECT:
            return {"format": {"type": "json_object"}}
        return None

    def _chat_response_format(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> dict[str, Any] | None:
        fmt = request.response_format or resolved.request_defaults.get("response_format")
        schema = request.json_schema or resolved.request_defaults.get("json_schema")
        strict = request.strict_json_schema or bool(resolved.request_defaults.get("strict_json_schema"))
        if fmt == LlmResponseFormatType.JSON_SCHEMA:
            return {"type": "json_schema", "json_schema": {"name": "structured_output", "schema": schema or {}, "strict": strict}}
        if fmt == LlmResponseFormatType.JSON_OBJECT:
            return {"type": "json_object"}
        return None

    def _validate_structured_output(self, request: LlmRequest, resolved: ResolvedLlmTarget) -> None:
        fmt = request.response_format or resolved.request_defaults.get("response_format")
        if fmt in {LlmResponseFormatType.JSON_OBJECT, LlmResponseFormatType.JSON_SCHEMA} and not resolved.model_config.supports_structured_output:
            raise LlmCapabilityError(f"model alias {resolved.model_config.alias} does not support structured output")

    @staticmethod
    def _message_to_responses_input(message: LlmMessage) -> dict[str, Any]:
        return {"role": message.role, "content": _content_to_responses_parts(message.content)}

    @staticmethod
    def _message_to_chat(message: LlmMessage) -> dict[str, Any]:
        return {"role": message.role, "content": _content_to_chat_content(message.content)}

    def _normalize_responses(self, raw: Any, request: LlmRequest, resolved: ResolvedLlmTarget) -> LlmResponse:
        content = getattr(raw, "output_text", None) or _extract_response_output_text(raw)
        return LlmResponse(
            content=content or "",
            model=resolved.model,
            model_alias=request.model_alias,
            provider_name=resolved.provider_config.provider_name,
            provider_type=resolved.provider_config.provider_type,
            raw=raw,
            usage=_normalize_usage(getattr(raw, "usage", None)),
            response_id=getattr(raw, "id", None),
            finish_reason=getattr(raw, "status", None),
        )

    def _normalize_chat(self, raw: Any, request: LlmRequest, resolved: ResolvedLlmTarget) -> LlmResponse:
        choice = _first(getattr(raw, "choices", None))
        message = getattr(choice, "message", None) if choice is not None else None
        content = getattr(message, "content", None) if message is not None else ""
        return LlmResponse(
            content=content or "",
            model=resolved.model,
            model_alias=request.model_alias,
            provider_name=resolved.provider_config.provider_name,
            provider_type=resolved.provider_config.provider_type,
            raw=raw,
            usage=_normalize_usage(getattr(raw, "usage", None)),
            response_id=getattr(raw, "id", None),
            finish_reason=getattr(choice, "finish_reason", None) if choice is not None else None,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self._client_factory is not None:
            self._client = self._client_factory(**self._client_kwargs())
            return self._client
        from openai import OpenAI

        self._client = OpenAI(**self._client_kwargs())
        return self._client

    def _client_kwargs(self) -> dict[str, Any]:
        api_key = os.environ.get(self.provider_config.api_key_env) if self.provider_config.api_key_env else None
        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "base_url": self.provider_config.base_url,
            "timeout": self.provider_config.timeout_sec,
            "max_retries": self.provider_config.max_retries,
            "default_headers": self.provider_config.extra_headers or None,
        }
        kwargs.update(self.provider_config.extra_client_kwargs)
        return {k: v for k, v in kwargs.items() if v is not None}


def _ad_hoc_model_config(model: str, provider_name: str):
    from sdk_test_agent.llm.llm_config import LlmModelConfig

    return LlmModelConfig(alias=model, provider_name=provider_name, model=model, supports_structured_output=True)


def _content_to_responses_parts(content: str | list[LlmContentPart]) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "input_text", "text": content}]
    return [_content_part_to_responses(part) for part in content]


def _content_part_to_responses(part: LlmContentPart) -> dict[str, Any]:
    if part.type in {"text", "input_text"}:
        return {"type": "input_text", "text": part.text or ""}
    data = {"type": part.type, **part.data}
    for key in ("text", "image_url", "file_id", "file_url", "detail"):
        value = getattr(part, key)
        if value is not None:
            data[key] = value
    return data


def _content_to_chat_content(content: str | list[LlmContentPart]) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    return [_content_part_to_chat(part) for part in content]


def _content_part_to_chat(part: LlmContentPart) -> dict[str, Any]:
    if part.type in {"text", "input_text"}:
        return {"type": "text", "text": part.text or ""}
    return _content_part_to_responses(part)


def _extract_response_output_text(raw: Any) -> str:
    chunks: list[str] = []
    for item in getattr(raw, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "".join(chunks)


def _normalize_usage(raw_usage: Any) -> LlmUsage | None:
    if raw_usage is None:
        return None
    if isinstance(raw_usage, dict):
        data = raw_usage
    else:
        data = {k: getattr(raw_usage, k) for k in dir(raw_usage) if not k.startswith("_") and isinstance(getattr(raw_usage, k), (int, dict, type(None)))}
    return LlmUsage(
        input_tokens=data.get("input_tokens") or data.get("prompt_tokens"),
        output_tokens=data.get("output_tokens") or data.get("completion_tokens"),
        total_tokens=data.get("total_tokens"),
        reasoning_tokens=(data.get("output_tokens_details") or {}).get("reasoning_tokens") if isinstance(data.get("output_tokens_details"), dict) else None,
        cached_input_tokens=(data.get("input_tokens_details") or {}).get("cached_tokens") if isinstance(data.get("input_tokens_details"), dict) else None,
        raw=data,
    )


def _first(value: Any) -> Any | None:
    return value[0] if value else None
