from __future__ import annotations

from typing import Any

from agent_crawler.loop.runner import CrawlerRunner
from agent_crawler.models.enums import RenderMode as CrawlRenderMode, TransportHint
from agent_crawler.models.request import CrawlRequest

from .result_mapper import map_crawl_result_to_web_result
from .tool_models import CacheMode, ToolRenderMode, TransportMode, WebReadPageResult, WebReadPageToolInput


class WebReadPageTool:
    name = "web.read_page"
    description = (
        "Read a webpage and return agent-friendly text, ranked chunks, links, quality score, "
        "authentication state, browser page references, cache metadata, and trace information."
    )

    def __init__(self, runner: CrawlerRunner) -> None:
        self.runner = runner

    async def arun(self, tool_input: WebReadPageToolInput | dict[str, Any]) -> WebReadPageResult:
        if isinstance(tool_input, dict):
            tool_input = WebReadPageToolInput(**tool_input)
        crawl_request = self._to_crawl_request(tool_input)
        crawl_result = await self.runner.run(crawl_request)
        return map_crawl_result_to_web_result(tool_input=tool_input, crawl_result=crawl_result)

    def _to_crawl_request(self, tool_input: WebReadPageToolInput) -> CrawlRequest:
        transport_hint = {
            "auto": TransportHint.AUTO,
            "http": TransportHint.HTTP,
            "browser": TransportHint.BROWSER,
        }[tool_input.transport]
        render_mode = CrawlRenderMode.PLAIN if tool_input.render_mode in ("agent_text", "both") else CrawlRenderMode.STRUCTURED
        return CrawlRequest(
            url=tool_input.url,
            query=tool_input.query,
            auth_profile_id=tool_input.auth_profile_id,
            render=tool_input.render_mode in ("agent_text", "both"),
            render_mode=render_mode,
            transport_hint=transport_hint,
            debug=tool_input.debug,
            options={
                "interactive_login": tool_input.interactive_login,
                "keep_page_open": tool_input.keep_page_open,
                "cache_mode": tool_input.cache_mode,
                "include_raw_html": tool_input.include_raw_html,
                "max_raw_html_chars": tool_input.max_raw_html_chars,
                "max_chunks": tool_input.max_chunks,
                "max_render_chars": tool_input.max_render_chars,
                "max_chunk_chars": tool_input.max_chunk_chars,
                "include_links": tool_input.include_links,
                "max_links": tool_input.max_links,
                "tool_render_mode": tool_input.render_mode,
            },
        )

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "The webpage URL to read."},
                "query": {"type": ["string", "null"], "description": "What information to focus on while reading the page."},
                "transport": {"type": "string", "enum": ["auto", "http", "browser"], "default": "auto"},
                "auth_profile_id": {"type": "string", "default": "anonymous"},
                "interactive_login": {"type": "boolean", "default": False},
                "keep_page_open": {"type": "boolean", "default": False},
                "render_mode": {"type": "string", "enum": ["agent_text", "chunks", "both", "none"], "default": "agent_text"},
                "max_chunks": {"type": "integer", "minimum": 0, "maximum": 50, "default": 8},
                "cache_mode": {"type": "string", "enum": ["prefer", "refresh", "bypass"], "default": "prefer"},
                "debug": {"type": "boolean", "default": False},
            },
        }


async def read_web_page(
    runner: CrawlerRunner,
    *,
    url: str,
    query: str | None = None,
    transport: TransportMode = "auto",
    auth_profile_id: str = "anonymous",
    interactive_login: bool = False,
    keep_page_open: bool = False,
    render_mode: ToolRenderMode = "agent_text",
    max_chunks: int = 8,
    cache_mode: CacheMode = "prefer",
    debug: bool = False,
) -> WebReadPageResult:
    tool = WebReadPageTool(runner)
    return await tool.arun(
        WebReadPageToolInput(
            url=url,
            query=query,
            transport=transport,
            auth_profile_id=auth_profile_id,
            interactive_login=interactive_login,
            keep_page_open=keep_page_open,
            render_mode=render_mode,
            max_chunks=max_chunks,
            cache_mode=cache_mode,
            debug=debug,
        )
    )
