from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .usage import LlmUsage

LlmContentPartType = Literal["text", "input_text", "image_url", "input_image", "input_file", "audio"]


@dataclass(slots=True)
class LlmContentPart:
    type: LlmContentPartType
    text: str | None = None
    image_url: str | None = None
    file_id: str | None = None
    file_url: str | None = None
    detail: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmMessage:
    role: str
    content: str | list[LlmContentPart]
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmStructuredOutputConfig:
    response_format: str = "text"
    schema_name: str | None = None
    json_schema: dict[str, Any] | None = None
    strict: bool = False


@dataclass(slots=True)
class LlmRequest:
    model_alias: str | None = None
    model: str | None = None
    messages: list[LlmMessage] = field(default_factory=list)
    instructions: str | None = None
    api_protocol: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    timeout_sec: float | None = None
    response_format: str | None = None
    json_schema: dict[str, Any] | None = None
    strict_json_schema: bool = False
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    reasoning_effort: str | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)

    @property
    def max_tokens(self) -> int | None:
        return self.max_output_tokens


@dataclass(slots=True)
class LlmResponse:
    content: str
    model: str | None = None
    model_alias: str | None = None
    provider_name: str | None = None
    provider_type: str | None = None
    raw: Any | None = None
    usage: LlmUsage | None = None
    finish_reason: str | None = None
    response_id: str | None = None
    request_id: str | None = None
    latency_ms: int | None = None
    parsed_json: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
