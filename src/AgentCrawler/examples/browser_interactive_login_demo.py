import asyncio

from agent_crawler.fetch.browser_fetcher import BrowserFetcher, BrowserFetcherConfig
from agent_crawler.fetch.auth_gate import BrowserAuthConfig


async def main() -> None:
    fetcher = BrowserFetcher(
        BrowserFetcherConfig(
            headless=False,
            keep_page_open=True,
            auth=BrowserAuthConfig(
                interactive_login=True,
                login_wait_timeout_ms=180_000,
            ),
        )
    )

    try:
        url = input("Target auth URL: ").strip()
        resp = await fetcher.fetch(url)

        print("status:", resp.status_code)
        print("final_url:", resp.final_url)
        print("auth_required:", resp.auth_required)
        print("auth_confidence:", resp.auth_confidence)
        print("auth_reason:", resp.auth_reason)
        print("interactive_login_used:", resp.interactive_login_used)
        print("interactive_login_success:", resp.interactive_login_success)
        print("login_wait_reason:", resp.login_wait_reason)
        print("before_density:", resp.before_login_density_score)
        print("after_density:", resp.after_login_density_score)
        print("html_len:", len(resp.html))
        print("page_ref:", resp.page_ref)

        input("Press Enter to close browser...")
    finally:
        await fetcher.aclose()


if __name__ == "__main__":
    asyncio.run(main())
