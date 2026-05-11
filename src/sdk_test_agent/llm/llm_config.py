from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .llm_enums import LlmApiProtocol
from .llm_models import LlmStructuredOutputConfig


@dataclass(slots=True)
class LlmProviderConfig:
    provider_name: str
    provider_type: str
    base_url: str | None = None
    api_key_env: str | None = None
    timeout_sec: float = 60.0
    max_retries: int = 2
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_client_kwargs: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmModelConfig:
    alias: str
    provider_name: str
    model: str
    api_protocol: str = LlmApiProtocol.RESPONSES
    temperature: float = 0.0
    top_p: float | None = None
    max_output_tokens: int | None = None
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_reasoning: bool = False
    reasoning_effort: str | None = None
    default_response_format: LlmStructuredOutputConfig | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmCallConfig:
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    timeout_sec: float | None = None
    stream: bool = False
    response_format: str | None = None
    json_schema: dict[str, Any] | None = None
    strict_json_schema: bool = False
    reasoning_effort: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    extra_body: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmRouteConfig:
    route_name: str
    primary_model_alias: str
    fallback_model_aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
