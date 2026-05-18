import asyncio

from agent_crawler.fetch.browser_fetcher import BrowserFetcher, BrowserFetcherConfig


async def main() -> None:
    fetcher = BrowserFetcher(
        BrowserFetcherConfig(
            headless=False,
            keep_page_open=True,
            page_ttl_s=600,
            max_open_pages=4,
        )
    )

    try:
        resp = await fetcher.fetch("https://github.com/YoungQuijote/sth_boring")

        print("status:", resp.status_code)
        print("final_url:", resp.final_url)
        print("page_ref:", resp.page_ref)
        print("context_ref:", resp.context_ref)
        print("kept_open:", resp.kept_open)

        input("Browser page is kept open. Press Enter to close all...")
    finally:
        await fetcher.aclose()


if __name__ == "__main__":
    asyncio.run(main())
