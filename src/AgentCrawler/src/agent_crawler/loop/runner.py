from __future__ import annotations

import uuid
from dataclasses import replace
from urllib.parse import urlparse

from agent_crawler.assess import QualityAssessor, RelevanceGate
from agent_crawler.emit import ArtifactAdapterForCrawler, EventLogger
from agent_crawler.extract import Cleaner, IntelligentExtractor, SimpleReranker, SiteAdapterRegistry, UniversalExtractor
from agent_crawler.fetch import HybridFetcher, ResultCache
from agent_crawler.models import (
    CrawlEvent,
    CrawlFailedError,
    CrawlPlan,
    CrawlRequest,
    CrawlResultBundle,
    ErrorType,
    EventStatus,
    EventStep,
    ExtractKind,
    RelevanceResult,
    TraceInfo,
)
from agent_crawler.policy import PolicyEngine
from agent_crawler.render import Renderer
from agent_crawler.session import SessionStore
from webkit.models import Document


class CrawlerRunner:
    def __init__(
        self,
        *,
        policy_engine: PolicyEngine | None = None,
        session_store: SessionStore | None = None,
        fetcher: HybridFetcher | None = None,
        universal_extractor: UniversalExtractor | None = None,
        adapter_registry: SiteAdapterRegistry | None = None,
        intelligent_extractor: IntelligentExtractor | None = None,
        cleaner: Cleaner | None = None,
        reranker: SimpleReranker | None = None,
        quality_assessor: QualityAssessor | None = None,
        relevance_gate: RelevanceGate | None = None,
        renderer: Renderer | None = None,
        event_logger: EventLogger | None = None,
        artifact_adapter: ArtifactAdapterForCrawler | None = None,
        result_cache: ResultCache | None = None,
    ):
        self.policy_engine = policy_engine or PolicyEngine()
        self.session_store = session_store or SessionStore()
        self.fetcher = fetcher or HybridFetcher()
        self.universal_extractor = universal_extractor or UniversalExtractor()
        self.adapter_registry = adapter_registry or SiteAdapterRegistry()
        self.intelligent_extractor = intelligent_extractor or IntelligentExtractor()
        self.cleaner = cleaner or Cleaner()
        self.reranker = reranker or SimpleReranker()
        self.quality_assessor = quality_assessor or QualityAssessor()
        self.relevance_gate = relevance_gate or RelevanceGate()
        self.renderer = renderer or Renderer()
        self.event_logger = event_logger or EventLogger()
        self.artifact_adapter = artifact_adapter or ArtifactAdapterForCrawler()
        self.result_cache = result_cache or ResultCache()

    async def run(self, request: CrawlRequest) -> CrawlResultBundle:
        run_id = uuid.uuid4().hex
        trace = TraceInfo(run_id=run_id)
        plan = self.policy_engine.build_plan(request)
        self._record(trace, request=request, plan=plan, attempt=0, step=EventStep.POLICY, status=EventStatus.OK, message="plan built")

        last_error_type = ErrorType.MAX_ATTEMPTS_EXCEEDED
        options = dict(getattr(request, "options", {}) or {})
        cache_mode = str(options.get("cache_mode", "prefer"))

        for attempt in range(1, max(1, request.max_attempts) + 1):
            cache_key = self.result_cache.make_key(request, plan)
            if plan.use_result_cache and cache_mode != "bypass":
                cached = self.result_cache.get(cache_key)
                if cached is not None and cache_mode != "refresh":
                    self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.CACHE, status=EventStatus.OK, message="result cache hit")
                    cached.trace = trace
                    if request.render and cached.rendered is None:
                        cached.rendered = self.renderer.render(cached.doc_clean, mode=request.render_mode)
                    return cached
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.CACHE, status=EventStatus.SKIPPED, message="result cache miss")

            session = self.session_store.get(request.url, request.auth_profile_id, plan.transport)
            self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.SESSION, status=EventStatus.OK, message="session ready")

            try:
                try:
                    fetched = await self.fetcher.fetch(request.url, plan=plan, session=session, options=options)
                except TypeError:
                    fetched = await self.fetcher.fetch(request.url, plan=plan, session=session)
                self._record(
                    trace,
                    request=request,
                    plan=plan,
                    attempt=attempt,
                    step=EventStep.FETCH,
                    status=EventStatus.OK,
                    final_url=fetched.meta.final_url,
                    status_code=fetched.meta.status_code,
                    elapsed_ms=fetched.meta.elapsed_ms,
                    message="fetch complete",
                )
            except NotImplementedError as exc:
                last_error_type = ErrorType.UNSUPPORTED_TRANSPORT
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.FETCH, status=EventStatus.ERROR, error_type=last_error_type, message=str(exc))
                plan = self._fallback(plan, trace, request, attempt, reason=str(exc))
                continue
            except Exception as exc:
                last_error_type = ErrorType.FETCH_ERROR
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.FETCH, status=EventStatus.ERROR, error_type=last_error_type, message=str(exc))
                plan = self._fallback(plan, trace, request, attempt, reason=str(exc))
                continue

            if fetched.meta.status_code >= 400:
                last_error_type = ErrorType.FETCH_ERROR
                reason = f"bad status {fetched.meta.status_code}"
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.FETCH, status=EventStatus.ERROR, error_type=last_error_type, message=reason)
                plan = self._fallback(plan, trace, request, attempt, reason=reason)
                continue

            try:
                doc = await self._extract(fetched.html or "", request=request, plan=plan)
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.EXTRACT, status=EventStatus.OK, final_url=fetched.meta.final_url, message="extract complete")
                self.cleaner.chunk(doc)
                doc.chunks = self.reranker.rank(doc.chunks, query=request.query)
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.CLEAN, status=EventStatus.OK, final_url=fetched.meta.final_url, chunk_count=len(doc.chunks), message="clean and rerank complete")
            except NotImplementedError as exc:
                last_error_type = ErrorType.UNSUPPORTED_EXTRACTOR
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.EXTRACT, status=EventStatus.ERROR, error_type=last_error_type, message=str(exc))
                plan = self._fallback(plan, trace, request, attempt, reason=str(exc))
                continue
            except Exception as exc:
                last_error_type = ErrorType.EXTRACT_ERROR
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.EXTRACT, status=EventStatus.ERROR, error_type=last_error_type, message=str(exc))
                plan = self._fallback(plan, trace, request, attempt, reason=str(exc))
                continue

            quality = self.quality_assessor.score(doc)
            self._record(
                trace,
                request=request,
                plan=plan,
                attempt=attempt,
                step=EventStep.ASSESS,
                status=EventStatus.OK if quality.ok else EventStatus.WARNING,
                final_url=fetched.meta.final_url,
                quality_score=quality.score,
                chunk_count=len(doc.chunks),
                message=",".join(quality.reasons) or "quality ok",
            )
            if not quality.ok:
                last_error_type = ErrorType.QUALITY_TOO_LOW
                plan = self._fallback(plan, trace, request, attempt, reason=",".join(quality.reasons))
                continue

            relevance: RelevanceResult | None = None
            if plan.allow_llm_gate and request.query:
                relevance = await self.relevance_gate.check(doc, query=request.query)
                if relevance and not relevance.relevant:
                    last_error_type = ErrorType.RELEVANCE_REJECTED
                    plan = self._fallback(plan, trace, request, attempt, reason=relevance.reason)
                    continue

            rendered = None
            if request.render:
                rendered = self.renderer.render(doc, mode=request.render_mode)
                self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.RENDER, status=EventStatus.OK, final_url=fetched.meta.final_url, message="render complete")

            bundle = CrawlResultBundle(
                request=request,
                plan=plan,
                fetched=fetched.meta,
                raw_html=fetched.html,
                doc_clean=doc,
                quality=quality,
                relevance=relevance,
                rendered=rendered,
                trace=trace,
            )
            if request.persist_artifacts:
                bundle.artifacts = self.artifact_adapter.persist(bundle)
            if plan.use_result_cache:
                self.result_cache.put(cache_key, bundle, ttl_s=plan.result_cache_ttl_s)
            self._record(trace, request=request, plan=plan, attempt=attempt, step=EventStep.EMIT, status=EventStatus.OK, final_url=fetched.meta.final_url, message="run complete")
            return bundle

        raise CrawlFailedError("crawl failed after fallback attempts", error_type=last_error_type, trace=trace)

    async def _extract(self, html: str, *, request: CrawlRequest, plan: CrawlPlan) -> Document:
        if plan.extract_kind == ExtractKind.UNIVERSAL:
            return self.universal_extractor.extract(html, url=request.url)
        if plan.extract_kind == ExtractKind.ADAPTER:
            adapter = self.adapter_registry.resolve(request.url, plan.adapter_name)
            if adapter is None:
                return self.universal_extractor.extract(html, url=request.url)
            return adapter.extract(html, url=request.url)
        if plan.extract_kind == ExtractKind.INTELLIGENT:
            return await self.intelligent_extractor.extract(html, url=request.url, query=request.query)
        return self.universal_extractor.extract(html, url=request.url)

    def _fallback(self, plan: CrawlPlan, trace: TraceInfo, request: CrawlRequest, attempt: int, *, reason: str) -> CrawlPlan:
        next_plan = self.policy_engine.update_plan_on_failure(plan)
        if next_plan == plan:
            next_plan = replace(plan, extract_kind=ExtractKind.INTELLIGENT)
        if next_plan != plan:
            trace.fallback_count += 1
        self._record(trace, request=request, plan=next_plan, attempt=attempt, step=EventStep.FALLBACK, status=EventStatus.WARNING, message=reason, fallback_reason=reason)
        return next_plan

    def _record(
        self,
        trace: TraceInfo,
        *,
        request: CrawlRequest,
        plan: CrawlPlan,
        attempt: int,
        step: EventStep,
        status: EventStatus,
        message: str = "",
        final_url: str | None = None,
        status_code: int | None = None,
        elapsed_ms: float | None = None,
        quality_score: float | None = None,
        chunk_count: int | None = None,
        fallback_reason: str | None = None,
        error_type: ErrorType | None = None,
    ) -> None:
        trace.add_step(
            attempt=attempt,
            step_name=step.value,
            status=status.value,
            reason=message,
            error_type=error_type,
            meta={"plan_transport": plan.transport.value, "plan_extract_kind": plan.extract_kind.value},
        )
        event = CrawlEvent(
            run_id=trace.run_id,
            attempt=attempt,
            step_name=step,
            status=status,
            url=request.url,
            final_url=final_url,
            domain=urlparse(request.url).netloc.lower(),
            transport=plan.transport,
            extractor=plan.extract_kind,
            adapter=plan.adapter_name,
            status_code=status_code,
            elapsed_ms=elapsed_ms,
            quality_score=quality_score,
            chunk_count=chunk_count,
            fallback_reason=fallback_reason,
            error_type=error_type,
            message=message,
        )
        self.event_logger.emit(event)
