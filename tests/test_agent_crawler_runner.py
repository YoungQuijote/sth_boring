from __future__ import annotations

import asyncio

from agent_crawler import CrawlerRunner, CrawlRequest, RenderMode
from agent_crawler.fetch.hybrid_fetcher import FetchedPayload
from agent_crawler.models import CrawlPlan, FetchMeta, TransportKind


class FakeFetcher:
    def __init__(self):
        self.calls = 0

    async def fetch(self, url: str, *, plan: CrawlPlan, session: object | None = None) -> FetchedPayload:
        self.calls += 1
        html = """
        <html>
          <head><title>Example test page</title></head>
          <body>
            <main>
              <h1>Example test page</h1>
              <p>This page contains enough useful text for the crawler quality gate to pass.</p>
              <p>The runner should fetch, extract, clean, rerank, assess, render, and cache this document.</p>
              <p>Additional words make the document comfortably longer than the minimum static threshold.</p>
              <p>Agent crawler architecture keeps policy, session, fetch, extract, assess, render, and emit separate.</p>
            </main>
            <a href="/docs">Docs</a>
          </body>
        </html>
        """
        return FetchedPayload(
            meta=FetchMeta(
                url=url,
                final_url=url,
                status_code=200,
                headers={"content-type": "text/html"},
                transport=TransportKind.HTTP,
            ),
            html=html,
            raw_bytes=html.encode("utf-8"),
        )


def test_runner_http_universal_render_and_cache() -> None:
    asyncio.run(_run_runner_http_universal_render_and_cache())


async def _run_runner_http_universal_render_and_cache() -> None:
    fetcher = FakeFetcher()
    runner = CrawlerRunner(fetcher=fetcher)  # type: ignore[arg-type]
    request = CrawlRequest(url="https://example.test/page", query="crawler", render=True, render_mode=RenderMode.STRUCTURED)

    first = await runner.run(request)
    second = await runner.run(request)

    assert fetcher.calls == 1
    assert first.fetched.status_code == 200
    assert first.doc_clean.title == "Example test page"
    assert first.quality.ok is True
    assert first.rendered is not None
    assert "Key chunks" in first.rendered
    assert second.doc_clean.text == first.doc_clean.text


def test_request_defaults_are_independent() -> None:
    a = CrawlRequest(url="https://a.example/")
    b = CrawlRequest(url="https://b.example/")

    assert a.budgets is not b.budgets
    assert a.max_attempts == 3
