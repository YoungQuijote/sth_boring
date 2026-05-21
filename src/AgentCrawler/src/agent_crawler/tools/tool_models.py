from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Literal

TransportMode = Literal["auto", "http", "browser"]
ToolRenderMode = Literal["agent_text", "chunks", "both", "none"]
CacheMode = Literal["prefer", "refresh", "bypass"]
ReadStatus = Literal[
    "success",
    "auth_required",
    "low_quality",
    "fetch_error",
    "extract_error",
    "timeout",
    "blocked",
    "config_error",
    "unknown_error",
]


@dataclass(slots=True)
class WebReadPageToolInput:
    url: str
    query: str | None = None
    transport: TransportMode = "auto"
    auth_profile_id: str = "anonymous"
    interactive_login: bool = False
    keep_page_open: bool = False
    render_mode: ToolRenderMode = "agent_text"
    max_chunks: int = 8
    max_render_chars: int = 12_000
    max_chunk_chars: int = 1_500
    include_links: bool = True
    max_links: int = 30
    include_raw_html: bool = False
    max_raw_html_chars: int = 5_000
    cache_mode: CacheMode = "prefer"
    debug: bool = False


@dataclass(slots=True)
class WebPageMeta:
    requested_url: str
    final_url: str | None = None
    title: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    transport_used: Literal["http", "browser"] | None = None


@dataclass(slots=True)
class WebChunk:
    chunk_id: str
    order: int
    rank: int | None = None
    score: float | None = None
    text: str = ""
    title: str | None = None
    source_url: str | None = None
    char_count: int = 0
    truncated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WebPageContent:
    rendered_text: str | None = None
    clean_text_preview: str | None = None
    raw_html_preview: str | None = None
    chunks: list[WebChunk] = field(default_factory=list)
    chunk_view: Literal["ranked", "original"] = "ranked"
    total_text_chars: int = 0
    total_chunks: int = 0
    truncated: bool = False


@dataclass(slots=True)
class WebLink:
    text: str
    url: str
    kind: Literal["internal", "external", "unknown"] = "unknown"
    rank: int | None = None


@dataclass(slots=True)
class WebLinksInfo:
    links: list[WebLink] = field(default_factory=list)
    total_links: int = 0
    truncated: bool = False


@dataclass(slots=True)
class WebQualityInfo:
    score: float = 0.0
    label: Literal["good", "medium", "poor", "unknown"] = "unknown"
    text_chars: int = 0
    chunk_count: int = 0
    link_count: int = 0
    reason: str | None = None
    fallback_triggered: bool = False
    fallback_reason: str | None = None


@dataclass(slots=True)
class WebAuthInfo:
    auth_required: bool = False
    confidence: float = 0.0
    reason: str | None = None
    interactive_login_used: bool = False
    interactive_login_success: bool | None = None
    auth_profile_id: str = "anonymous"
    storage_state_used: bool = False
    storage_state_saved: bool = False
    before_login_url: str | None = None
    after_login_url: str | None = None
    before_density_score: float | None = None
    after_density_score: float | None = None


@dataclass(slots=True)
class WebBrowserInfo:
    page_ref: str | None = None
    context_ref: str | None = None
    kept_open: bool = False
    headless: bool | None = None
    browser_name: str | None = None
    redirect_chain: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WebCacheInfo:
    cache_hit: bool = False
    cache_key: str | None = None
    age_s: float | None = None
    ttl_s: float | None = None
    cache_mode: CacheMode = "prefer"


@dataclass(slots=True)
class WebArtifactRefs:
    raw_html_ref: str | None = None
    clean_text_ref: str | None = None
    rendered_text_ref: str | None = None
    screenshot_ref: str | None = None
    trace_ref: str | None = None


@dataclass(slots=True)
class WebTraceInfo:
    run_id: str | None = None
    attempts: int = 1
    fallback_chain: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WebErrorInfo:
    error_type: str
    message: str
    retryable: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WebReadPageResult:
    ok: bool
    status: ReadStatus
    page: WebPageMeta
    content: WebPageContent
    links: WebLinksInfo
    quality: WebQualityInfo
    auth: WebAuthInfo
    browser: WebBrowserInfo | None = None
    cache: WebCacheInfo | None = None
    artifacts: WebArtifactRefs | None = None
    trace: WebTraceInfo | None = None
    error: WebErrorInfo | None = None


def to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, tuple):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, Enum):
        return obj.value
    return obj


def result_to_dict(result: WebReadPageResult) -> dict[str, Any]:
    return to_jsonable(result)
