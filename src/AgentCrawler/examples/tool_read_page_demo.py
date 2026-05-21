from __future__ import annotations

import argparse
import asyncio
import json

from agent_crawler.loop.runner import CrawlerRunner
from agent_crawler.tools.tool_models import WebReadPageToolInput, result_to_dict
from agent_crawler.tools.web_read_page import WebReadPageTool


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--query", default=None)
    parser.add_argument("--transport", choices=["auto", "http", "browser"], default="auto")
    parser.add_argument("--render-mode", choices=["agent_text", "chunks", "both", "none"], default="agent_text")
    parser.add_argument("--interactive-login", action="store_true")
    parser.add_argument("--keep-page-open", action="store_true")
    parser.add_argument("--max-chunks", type=int, default=8)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    runner = CrawlerRunner()
    tool = WebReadPageTool(runner)

    result = await tool.arun(
        WebReadPageToolInput(
            url=args.url,
            query=args.query,
            transport=args.transport,
            render_mode=args.render_mode,
            interactive_login=args.interactive_login,
            keep_page_open=args.keep_page_open,
            max_chunks=args.max_chunks,
            debug=args.debug,
        )
    )

    print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
