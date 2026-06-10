import asyncio
import sys

from agent_crawler import CrawlerRunner, CrawlRequest, RenderMode


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"
    runner = CrawlerRunner()
    bundle = await runner.run(CrawlRequest(url=url, render=True, render_mode=RenderMode.PLAIN))
    print(f"status={bundle.fetched.status_code} final_url={bundle.fetched.final_url}")
    print(f"title={bundle.doc_clean.title}")
    print(f"quality={bundle.quality.score:.3f} chunks={len(bundle.doc_clean.chunks)}")
    if bundle.rendered:
        print(bundle.rendered[:1000])


if __name__ == "__main__":
    asyncio.run(main())
