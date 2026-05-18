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

    async def fetch(self, url: str, *, plan: CrawlPlan, session: object | None = None) -> FetchedPayload:
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

        resp = await self.browser_fetcher.fetch(url, session=session)
        elapsed_ms = resp.elapsed_ms or (time.monotonic() - started) * 1000.0
        return FetchedPayload(
            meta=FetchMeta(
                url=url,
                final_url=resp.final_url,
                status_code=resp.status_code,
                headers=resp.headers,
                elapsed_ms=elapsed_ms,
                transport=TransportKind.BROWSER,
            ),
            html=resp.html,
            raw_bytes=resp.html.encode("utf-8"),
        )
