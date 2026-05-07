from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LlmMessage:
    role: str
    content: str


@dataclass(slots=True)
class LlmRequest:
    model: str
    messages: list[LlmMessage]
    temperature: float = 0.0
    max_tokens: int | None = None
    response_format: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmResponse:
    content: str
    raw: Any | None = None
    model: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
