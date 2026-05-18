import asyncio
from pathlib import Path

from agent_crawler.fetch.browser_fetcher import BrowserFetcher, BrowserFetcherConfig
from agent_crawler.models import TransportKind
from agent_crawler.session import AuthProfile, CrawlSession


async def main() -> None:
    storage_state_path = Path(".agent_crawler_storage_state/demo_state.json")
    session = CrawlSession(
        domain="github.com",
        auth_profile=AuthProfile(profile_id="demo", storage_state_path=str(storage_state_path)),
        transport=TransportKind.BROWSER,
    )
    fetcher = BrowserFetcher(BrowserFetcherConfig(headless=True, keep_page_open=False))

    try:
        resp = await fetcher.fetch("https://github.com/YoungQuijote/sth_boring", session=session)
        print("status:", resp.status_code)
        print("final_url:", resp.final_url)
        print("html_len:", len(resp.html))
        print("storage_state_path:", storage_state_path)
        print("storage_state_exists:", storage_state_path.exists())
    finally:
        await fetcher.aclose()


if __name__ == "__main__":
    asyncio.run(main())
