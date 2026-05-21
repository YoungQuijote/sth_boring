from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ExtractHint, RenderMode, TransportHint


@dataclass(frozen=True)
class CrawlBudgets:
    max_pages: int = 1
    max_elapsed_s: float = 30.0
    max_llm_tokens: int = 0
    max_raw_html_chars: int = 2_000_000


@dataclass(frozen=True)
class LLMConfig:
    provider: str | None = None
    model: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None


@dataclass(frozen=True)
class CrawlRequest:
    url: str
    query: str | None = None
    auth_profile_id: str = "anonymous"
    render: bool = False
    render_mode: RenderMode = RenderMode.PLAIN
    transport_hint: TransportHint = TransportHint.AUTO
    extract_hint: ExtractHint = ExtractHint.AUTO
    max_attempts: int = 3
    budgets: CrawlBudgets = field(default_factory=CrawlBudgets)
    persist_artifacts: bool = False
    debug: bool = False
    llm: LLMConfig | None = None
    options: dict[str, object] = field(default_factory=dict)
