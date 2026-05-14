from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import ErrorType, EventStatus, EventStep, ExtractKind, TransportKind


@dataclass(frozen=True)
class CrawlEvent:
    run_id: str
    attempt: int
    step_name: EventStep | str
    status: EventStatus | str
    url: str
    final_url: str | None = None
    domain: str | None = None
    transport: TransportKind | str | None = None
    extractor: ExtractKind | str | None = None
    adapter: str | None = None
    status_code: int | None = None
    elapsed_ms: float | None = None
    retries: int = 0
    quality_score: float | None = None
    chunk_count: int | None = None
    fallback_reason: str | None = None
    error_type: ErrorType | str | None = None
    message: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        data["created_at"] = self.created_at.isoformat()
        for key in ("step_name", "status", "transport", "extractor", "error_type"):
            value = data.get(key)
            if hasattr(value, "value"):
                data[key] = value.value
        return data
