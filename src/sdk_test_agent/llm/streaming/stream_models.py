from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LlmStreamEvent:
    event_type: str
    delta: str | None = None
    content: str | None = None
    raw: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
