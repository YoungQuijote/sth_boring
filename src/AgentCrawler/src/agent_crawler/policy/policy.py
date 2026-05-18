from __future__ import annotations

from dataclasses import replace

from agent_crawler.models import CrawlPlan, CrawlRequest, ExtractHint, ExtractKind, FetchMeta, QualityScore, TransportHint, TransportKind

from .domain_policy import DomainPolicyRegistry


class PolicyEngine:
    def __init__(self, domain_registry: DomainPolicyRegistry | None = None):
        self.domain_registry = domain_registry or DomainPolicyRegistry()

    def build_plan(self, request: CrawlRequest) -> CrawlPlan:
        domain_policy = self.domain_registry.resolve(request.url)

        transport = TransportKind.HTTP
        if request.transport_hint == TransportHint.BROWSER or (
            request.transport_hint == TransportHint.AUTO and domain_policy.prefer_browser
        ):
            transport = TransportKind.BROWSER

        extract_kind = ExtractKind.UNIVERSAL
        adapter_name = domain_policy.adapter_name
        if request.extract_hint == ExtractHint.ADAPTER or (
            request.extract_hint == ExtractHint.AUTO and adapter_name
        ):
            extract_kind = ExtractKind.ADAPTER
        elif request.extract_hint == ExtractHint.INTELLIGENT:
            extract_kind = ExtractKind.INTELLIGENT
        elif request.extract_hint == ExtractHint.UNIVERSAL:
            extract_kind = ExtractKind.UNIVERSAL
            adapter_name = None

        return CrawlPlan(
            transport=transport,
            extract_kind=extract_kind,
            adapter_name=adapter_name,
            prefer_profile=domain_policy.prefer_profile or domain_policy.requires_auth,
            result_cache_ttl_s=domain_policy.result_cache_ttl_s,
            http_cache_ttl_s=domain_policy.http_cache_ttl_s,
            allow_llm_gate=domain_policy.allow_llm_gate,
            allow_llm_render=domain_policy.allow_llm_render,
        )

    def update_plan_on_failure(
        self,
        plan: CrawlPlan,
        quality: QualityScore | None = None,
        fetched: FetchMeta | None = None,
    ) -> CrawlPlan:
        if plan.transport == TransportKind.HTTP and plan.extract_kind == ExtractKind.UNIVERSAL and plan.adapter_name:
            return replace(plan, extract_kind=ExtractKind.ADAPTER)
        if plan.transport == TransportKind.HTTP:
            return replace(plan, transport=TransportKind.BROWSER, extract_kind=ExtractKind.UNIVERSAL)
        if plan.transport == TransportKind.BROWSER and plan.adapter_name and plan.extract_kind != ExtractKind.ADAPTER:
            return replace(plan, extract_kind=ExtractKind.ADAPTER)
        if plan.extract_kind != ExtractKind.INTELLIGENT:
            return replace(plan, extract_kind=ExtractKind.INTELLIGENT)
        return plan
