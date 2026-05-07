from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LlmModelConfig:
    model: str
    provider: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None
