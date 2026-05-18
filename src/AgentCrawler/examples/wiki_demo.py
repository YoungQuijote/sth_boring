import asyncio
import sys
from urllib.parse import quote

from webkit.fetchers.http import HttpFetcher, HostLimiter, DiskCache
from webkit.pipeline.clean import Cleaner
from webkit.pipeline.rerank import SimpleReranker
from webkit.spiders.wiki import WikiSpider


async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Berlin"
    url = f"https://en.wikipedia.org/wiki/{quote(query.replace(' ', '_'))}"

    limiter = HostLimiter(max_concurrency_per_host=2, min_interval_s=0.5)
    cache = DiskCache(cache_dir=".webcache", ttl_s=3600)

    async with HttpFetcher(limiter=limiter, cache=cache) as fetcher:
        spider = WikiSpider(fetcher=fetcher, cleaner=Cleaner(), reranker=SimpleReranker())
        doc = await spider.crawl(url, query=query)

    print(f"URL: {doc.url}")
    print(f"Title: {doc.title}")
    print("=" * 80)
    for i, ch in enumerate(doc.chunks[:8], start=1):
        print(f"[{i}] score={ch.score:.4f} order={ch.order}")
        print(ch.text[:800].strip())
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
