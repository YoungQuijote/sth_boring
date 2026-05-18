import asyncio
import sys

from agent_crawler import CrawlerRunner, CrawlRequest, RenderMode


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"
    query = sys.argv[2] if len(sys.argv) > 2 else None
    runner = CrawlerRunner()
    bundle = await runner.run(
        CrawlRequest(
            url=url,
            query=query,
            render=True,
            render_mode=RenderMode.STRUCTURED,
        )
    )
    print(f"URL: {bundle.fetched.final_url}")
    print(f"Title: {bundle.doc_clean.title}")
    print(f"Quality: {bundle.quality.score:.3f} reasons={bundle.quality.reasons}")
    print("=" * 80)
    print(bundle.rendered or bundle.doc_clean.text[:2000])


if __name__ == "__main__":
    asyncio.run(main())
