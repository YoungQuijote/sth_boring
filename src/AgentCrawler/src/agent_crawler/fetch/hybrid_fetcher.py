from __future__ import annotations

import time
from dataclasses import dataclass

from agent_crawler.models import CrawlPlan, FetchMeta, TransportKind

from .browser_fetcher import BrowserFetcher
from .http_fetcher import HttpFetcher


@dataclass
class FetchedPayload:
    meta: FetchMeta
    html: str | None
    raw_bytes: bytes | None = None


class HybridFetcher:
    def __init__(self, *, http_fetcher: HttpFetcher | None = None, browser_fetcher: BrowserFetcher | None = None):
        self.http_fetcher = http_fetcher
        self.browser_fetcher = browser_fetcher or BrowserFetcher()

    async def fetch(self, url: str, *, plan: CrawlPlan, session: object | None = None, options: dict[str, object] | None = None) -> FetchedPayload:
        started = time.monotonic()
        if plan.transport == TransportKind.HTTP:
            if self.http_fetcher is None:
                self.http_fetcher = HttpFetcher(cache=None)
            resp = await self.http_fetcher.fetch(url)
            elapsed_ms = (time.monotonic() - started) * 1000.0
            return FetchedPayload(
                meta=FetchMeta(
                    url=resp.url,
                    final_url=resp.final_url,
                    status_code=resp.status_code,
                    headers=resp.headers,
                    elapsed_ms=elapsed_ms,
                    fetched_at=resp.fetched_at,
                    transport=TransportKind.HTTP,
                ),
                html=resp.text(),
                raw_bytes=resp.content,
            )

        opts = options or {}
        resp = await self.browser_fetcher.fetch(
            url,
            session=session,
            keep_page_open=bool(opts.get("keep_page_open", False)),
            interactive_login=bool(opts.get("interactive_login", False)),
        )
        elapsed_ms = resp.elapsed_ms or (time.monotonic() - started) * 1000.0
        return FetchedPayload(
            meta=FetchMeta(
                url=url,
                final_url=resp.final_url,
                status_code=resp.status_code,
                headers=resp.headers,
                elapsed_ms=elapsed_ms,
                transport=TransportKind.BROWSER,
                extra={
                    "auth_required": getattr(resp, "auth_required", False),
                    "auth_confidence": getattr(resp, "auth_confidence", 0.0),
                    "auth_reason": getattr(resp, "auth_reason", None),
                    "interactive_login_used": getattr(resp, "interactive_login_used", False),
                    "interactive_login_success": getattr(resp, "interactive_login_success", None),
                    "before_login_url": getattr(resp, "before_login_url", None),
                    "after_login_url": getattr(resp, "after_login_url", None),
                    "before_login_density_score": getattr(resp, "before_login_density_score", None),
                    "after_login_density_score": getattr(resp, "after_login_density_score", None),
                    "page_ref": getattr(resp, "page_ref", None),
                    "context_ref": getattr(resp, "context_ref", None),
                    "kept_open": getattr(resp, "kept_open", False),
                    "redirect_chain": getattr(resp, "redirect_chain", []),
                    "storage_state_used": bool(getattr(resp, "storage_state_used", False)),
                    "storage_state_saved": bool(getattr(resp, "storage_state_saved", False)),
                },
            ),
            html=resp.html,
            raw_bytes=resp.html.encode("utf-8"),
        )
