from __future__ import annotations

from enum import Enum


class TransportHint(str, Enum):
    AUTO = "auto"
    HTTP = "http"
    BROWSER = "browser"


class TransportKind(str, Enum):
    HTTP = "http"
    BROWSER = "browser"


class ExtractHint(str, Enum):
    AUTO = "auto"
    UNIVERSAL = "universal"
    ADAPTER = "adapter"
    INTELLIGENT = "intelligent"


class ExtractKind(str, Enum):
    UNIVERSAL = "universal"
    ADAPTER = "adapter"
    INTELLIGENT = "intelligent"


class RenderMode(str, Enum):
    PLAIN = "plain"
    STRUCTURED = "structured"
    ADAPTER = "adapter"
    LLM = "llm"


class ErrorType(str, Enum):
    FETCH_ERROR = "fetch_error"
    EXTRACT_ERROR = "extract_error"
    QUALITY_TOO_LOW = "quality_too_low"
    RELEVANCE_REJECTED = "relevance_rejected"
    UNSUPPORTED_TRANSPORT = "unsupported_transport"
    UNSUPPORTED_EXTRACTOR = "unsupported_extractor"
    MAX_ATTEMPTS_EXCEEDED = "max_attempts_exceeded"


class EventStatus(str, Enum):
    STARTED = "started"
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class EventStep(str, Enum):
    POLICY = "policy"
    CACHE = "cache"
    SESSION = "session"
    FETCH = "fetch"
    EXTRACT = "extract"
    CLEAN = "clean"
    ASSESS = "assess"
    RENDER = "render"
    EMIT = "emit"
    FALLBACK = "fallback"
