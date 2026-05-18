from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from webkit.models import Document

from .enums import ErrorType, ExtractKind, TransportKind
from .plan import CrawlPlan
from .request import CrawlRequest


@dataclass(frozen=True)
class FetchMeta:
    url: str
    final_url: str
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    retries: int = 0
    fetched_at: datetime | None = None
    transport: TransportKind = TransportKind.HTTP


@dataclass(frozen=True)
class QualityScore:
    score: float
    ok: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelevanceResult:
    relevant: bool
    confidence: float
    reason: str = ""


@dataclass(frozen=True)
class ArtifactRefs:
    raw_html_ref: str | None = None
    document_ref: str | None = None
    rendered_ref: str | None = None
    debug_ref: str | None = None


@dataclass(frozen=True)
class TraceStep:
    attempt: int
    step_name: str
    status: str
    reason: str = ""
    error_type: ErrorType | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceInfo:
    run_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    fallback_count: int = 0
    steps: list[TraceStep] = field(default_factory=list)

    def add_step(
        self,
        *,
        attempt: int,
        step_name: str,
        status: str,
        reason: str = "",
        error_type: ErrorType | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.steps.append(
            TraceStep(
                attempt=attempt,
                step_name=step_name,
                status=status,
                reason=reason,
                error_type=error_type,
                meta=meta or {},
            )
        )


@dataclass
class CrawlResultBundle:
    request: CrawlRequest
    plan: CrawlPlan
    fetched: FetchMeta
    raw_html: str | None
    doc_clean: Document
    quality: QualityScore
    relevance: RelevanceResult | None = None
    rendered: str | None = None
    trace: TraceInfo | None = None
    artifacts: ArtifactRefs | None = None


class CrawlFailedError(RuntimeError):
    def __init__(self, message: str, *, error_type: ErrorType, trace: TraceInfo):
        super().__init__(message)
        self.error_type = error_type
        self.trace = trace
