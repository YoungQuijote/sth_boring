import asyncio

from agent_crawler.fetch.browser_fetcher import BrowserFetcher, BrowserFetcherConfig


async def main() -> None:
    fetcher = BrowserFetcher(
        BrowserFetcherConfig(
            headless=True,
            keep_page_open=False,
        )
    )

    try:
        resp = await fetcher.fetch("https://github.com/YoungQuijote/sth_boring")
        print("status:", resp.status_code)
        print("final_url:", resp.final_url)
        print("html_len:", len(resp.html))
        print("kept_open:", resp.kept_open)
        print(resp.html[:300])
    finally:
        await fetcher.aclose()


if __name__ == "__main__":
    asyncio.run(main())
