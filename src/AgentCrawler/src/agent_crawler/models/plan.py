from __future__ import annotations

from dataclasses import dataclass

from .enums import ExtractKind, TransportKind


@dataclass(frozen=True)
class CrawlPlan:
    transport: TransportKind
    extract_kind: ExtractKind
    adapter_name: str | None = None
    prefer_profile: bool = False
    use_result_cache: bool = True
    result_cache_ttl_s: int = 600
    http_cache_ttl_s: int = 3600
    allow_llm_gate: bool = False
    allow_llm_render: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    plan: CrawlPlan
    reason: str
