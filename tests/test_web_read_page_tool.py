from __future__ import annotations

import asyncio

from agent_crawler import CrawlerRunner
from agent_crawler.fetch.hybrid_fetcher import FetchedPayload
from agent_crawler.models import CrawlPlan, FetchMeta, TransportKind
from agent_crawler.tools import WebReadPageTool, WebReadPageToolInput


class FakeFetcher:
    async def fetch(self, url: str, *, plan: CrawlPlan, session: object | None = None, options: dict[str, object] | None = None) -> FetchedPayload:
        html = """
        <html><head><title>Tool page</title></head>
        <body><main>
        <p>This page contains enough useful text for tool output mapping validation.</p>
        <p>It should become rendered text and ranked chunks for agent consumption. This additional sentence ensures the cleaned text length is comfortably above the quality threshold used by the assessor in the runner pipeline.</p>
        </main>
        <a href='/docs'>Docs</a>
        </body></html>
        """
        return FetchedPayload(
            meta=FetchMeta(url=url, final_url=url, status_code=200, headers={"content-type": "text/html"}, transport=TransportKind.HTTP),
            html=html,
            raw_bytes=html.encode("utf-8"),
        )


def test_web_read_page_tool_success() -> None:
    asyncio.run(_run_success())


async def _run_success() -> None:
    runner = CrawlerRunner(fetcher=FakeFetcher())  # type: ignore[arg-type]
    tool = WebReadPageTool(runner)
    result = await tool.arun(
        WebReadPageToolInput(
            url="https://example.test/page",
            query="crawler",
            render_mode="both",
            max_chunks=3,
        )
    )
    assert result.ok is True
    assert result.status == "success"
    assert result.page.final_url == "https://example.test/page"
    assert result.content.total_chunks >= 1
    assert len(result.content.chunks) <= 3
    assert result.quality.score > 0


def test_web_read_page_tool_input_schema_shape() -> None:
    runner = CrawlerRunner(fetcher=FakeFetcher())  # type: ignore[arg-type]
    tool = WebReadPageTool(runner)
    schema = tool.input_schema()
    assert schema["type"] == "object"
    assert "url" in schema["required"]
    assert "transport" in schema["properties"]
