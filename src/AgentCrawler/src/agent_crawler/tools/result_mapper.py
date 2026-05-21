from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .tool_models import (
    WebAuthInfo,
    WebBrowserInfo,
    WebCacheInfo,
    WebChunk,
    WebErrorInfo,
    WebLink,
    WebLinksInfo,
    WebPageContent,
    WebPageMeta,
    WebQualityInfo,
    WebReadPageResult,
    WebReadPageToolInput,
    WebTraceInfo,
)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _truncate_text(text: str | None, limit: int) -> tuple[str | None, bool]:
    if text is None:
        return None, False
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n...[truncated]", True


def _quality_label(score: float) -> str:
    if score >= 0.70:
        return "good"
    if score >= 0.40:
        return "medium"
    return "poor"


def map_crawl_result_to_web_result(*, tool_input: WebReadPageToolInput, crawl_result: Any) -> WebReadPageResult:
    fetched = _get(crawl_result, "fetched")
    doc = _get(crawl_result, "doc_clean")
    quality = _get(crawl_result, "quality")
    trace = _get(crawl_result, "trace")
    rendered = _get(crawl_result, "rendered")
    extra = _get(fetched, "extra", {}) or {}

    requested_url = _get(_get(crawl_result, "request"), "url", tool_input.url)
    final_url = _get(fetched, "final_url", requested_url)
    headers = _get(fetched, "headers", {}) or {}
    status_code = _get(fetched, "status_code")
    transport_used = _get(_get(fetched, "transport"), "value", _get(fetched, "transport"))
    if transport_used not in ("http", "browser"):
        transport_used = None

    page = WebPageMeta(
        requested_url=requested_url,
        final_url=final_url,
        title=_get(doc, "title"),
        status_code=status_code,
        content_type=headers.get("content-type") if isinstance(headers, dict) else None,
        transport_used=transport_used,
    )

    chunks_src = list(_get(doc, "chunks", []) or [])
    out_chunks: list[WebChunk] = []
    for rank, chunk in enumerate(chunks_src[: max(0, tool_input.max_chunks)]):
        txt, trunc = _truncate_text(_get(chunk, "text", "") or "", tool_input.max_chunk_chars)
        out_chunks.append(
            WebChunk(
                chunk_id=f"chunk_{rank:04d}",
                order=int(_get(chunk, "order", rank) or rank),
                rank=rank,
                score=_get(chunk, "score"),
                text=txt or "",
                title=_get(chunk, "title"),
                source_url=_get(chunk, "source_url", final_url),
                char_count=len(txt or ""),
                truncated=trunc,
                metadata=dict(_get(chunk, "meta", {}) or {}),
            )
        )

    rendered_text = None
    clean_preview = _get(doc, "text", None)
    raw_preview = None
    content_trunc = False
    if tool_input.include_raw_html:
        raw_preview, raw_tr = _truncate_text(_get(crawl_result, "raw_html"), tool_input.max_raw_html_chars)
        content_trunc = content_trunc or raw_tr

    if tool_input.render_mode in ("agent_text", "both"):
        candidate = rendered or clean_preview
        rendered_text, tr = _truncate_text(candidate, tool_input.max_render_chars)
        content_trunc = content_trunc or tr
    elif tool_input.render_mode == "none":
        rendered_text = None
    elif tool_input.render_mode == "chunks":
        rendered_text = None

    clean_preview, tr2 = _truncate_text(clean_preview, tool_input.max_render_chars)
    content_trunc = content_trunc or tr2

    content = WebPageContent(
        rendered_text=rendered_text,
        clean_text_preview=clean_preview,
        raw_html_preview=raw_preview,
        chunks=out_chunks if tool_input.render_mode in ("chunks", "both", "agent_text") else [],
        total_text_chars=len(_get(doc, "text", "") or ""),
        total_chunks=len(chunks_src),
        truncated=content_trunc,
    )

    links_src = list(_get(doc, "links", []) or [])
    out_links: list[WebLink] = []
    for i, link in enumerate(links_src[: max(0, tool_input.max_links)]):
        if isinstance(link, str):
            url = link
            text = ""
        else:
            url = _get(link, "url", _get(link, "href", "")) or ""
            text = _get(link, "text", "") or ""
        kind = "unknown"
        try:
            base_host = urlparse(requested_url).netloc
            link_host = urlparse(url).netloc
            if link_host and base_host:
                kind = "internal" if link_host == base_host else "external"
        except Exception:
            pass
        out_links.append(WebLink(text=text, url=url, kind=kind, rank=i))
    links = WebLinksInfo(links=out_links if tool_input.include_links else [], total_links=len(links_src), truncated=len(links_src) > tool_input.max_links)

    q_score = float(_get(quality, "score", 0.0) or 0.0)
    q_reason = ",".join(_get(quality, "reasons", []) or []) or None
    quality_info = WebQualityInfo(
        score=q_score,
        label=_quality_label(q_score) if _get(quality, "score") is not None else "unknown",
        text_chars=int((_get(quality, "metrics", {}) or {}).get("text_chars", len(_get(doc, "text", "") or ""))),
        chunk_count=int((_get(quality, "metrics", {}) or {}).get("chunk_count", len(chunks_src))),
        link_count=int((_get(quality, "metrics", {}) or {}).get("link_count", len(links_src))),
        reason=q_reason,
        fallback_triggered=bool(_get(trace, "fallback_count", 0)),
        fallback_reason=(_get(trace, "steps", []) or [None])[-1].reason if _get(trace, "steps", []) else None,
    )

    auth = WebAuthInfo(
        auth_required=bool(extra.get("auth_required", False)),
        confidence=float(extra.get("auth_confidence", 0.0) or 0.0),
        reason=extra.get("auth_reason"),
        interactive_login_used=bool(extra.get("interactive_login_used", False)),
        interactive_login_success=extra.get("interactive_login_success"),
        auth_profile_id=tool_input.auth_profile_id,
        storage_state_used=bool(extra.get("storage_state_used", False)),
        storage_state_saved=bool(extra.get("storage_state_saved", False)),
        before_login_url=extra.get("before_login_url"),
        after_login_url=extra.get("after_login_url"),
        before_density_score=extra.get("before_login_density_score"),
        after_density_score=extra.get("after_login_density_score"),
    )

    ok, status, error = _derive_status(crawl_result, auth_required=auth.auth_required, quality_score=q_score)

    return WebReadPageResult(
        ok=ok,
        status=status,
        page=page,
        content=content,
        links=links,
        quality=quality_info,
        auth=auth,
        browser=WebBrowserInfo(
            page_ref=extra.get("page_ref"),
            context_ref=extra.get("context_ref"),
            kept_open=bool(extra.get("kept_open", False)),
            headless=extra.get("headless"),
            browser_name=extra.get("browser_name"),
            redirect_chain=list(extra.get("redirect_chain", []) or []),
        ) if transport_used == "browser" or extra else None,
        cache=WebCacheInfo(cache_hit=bool(extra.get("cache_hit", False)), cache_key=extra.get("cache_key"), cache_mode=tool_input.cache_mode),
        trace=WebTraceInfo(
            run_id=_get(trace, "run_id"),
            attempts=max(1, len(_get(trace, "steps", []) or [])),
            fallback_chain=[(_get(step, "meta", {}) or {}).get("plan_transport", "") for step in (_get(trace, "steps", []) or []) if _get(step, "step_name") == "fallback"],
            events=[f"{_get(step, 'step_name')}:{_get(step, 'status')}" for step in (_get(trace, "steps", []) or [])],
        ),
        error=error,
    )


def _derive_status(crawl_result: Any, *, auth_required: bool, quality_score: float) -> tuple[bool, str, WebErrorInfo | None]:
    if auth_required:
        return False, "auth_required", WebErrorInfo(
            error_type="auth_required",
            message="The page requires authentication. Retry with interactive_login=true or a valid auth_profile_id.",
            retryable=True,
        )
    if _get(crawl_result, "doc_clean") is None:
        return False, "extract_error", WebErrorInfo("extract_error", "The crawler did not produce a clean document.", True)
    if quality_score < 0.30:
        return False, "low_quality", WebErrorInfo("low_quality", "The crawler fetched the page but extracted low-quality content.", True)
    return True, "success", None
