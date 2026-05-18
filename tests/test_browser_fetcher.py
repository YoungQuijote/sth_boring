from __future__ import annotations

import asyncio
import time

from agent_crawler.fetch import BrowserFetcher, BrowserFetcherConfig, BrowserPageRegistry, HybridFetcher
from agent_crawler.models import CrawlPlan, ExtractKind, TransportKind
from agent_crawler.session import AuthProfile, CrawlSession


class FakeResponse:
    status = 207
    headers = {"x-test": "ok"}


class FakePage:
    def __init__(self, final_url: str = "https://example.test/rendered"):
        self.url = final_url
        self.closed = False
        self.goto_calls = []
        self.wait_calls = []

    async def goto(self, url: str, *, wait_until: str, timeout: int):
        self.goto_calls.append((url, wait_until, timeout))
        return FakeResponse()

    async def wait_for_load_state(self, state: str, *, timeout: int):
        self.wait_calls.append((state, timeout))

    async def content(self) -> str:
        return "<html><body><main>Rendered by fake browser.</main></body></html>"

    async def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, page: FakePage):
        self.page = page
        self.closed = False
        self.routes = []
        self.storage_state_paths = []

    async def route(self, pattern: str, handler):
        self.routes.append((pattern, handler))

    async def new_page(self) -> FakePage:
        return self.page

    async def storage_state(self, *, path: str) -> None:
        self.storage_state_paths.append(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"cookies": [], "origins": []}')

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self):
        self.contexts: list[FakeContext] = []
        self.context_kwargs: list[dict] = []
        self.closed = False

    async def new_context(self, **kwargs) -> FakeContext:
        page = FakePage()
        context = FakeContext(page)
        self.contexts.append(context)
        self.context_kwargs.append(kwargs)
        return context

    async def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self):
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


class FakeRouteRequest:
    def __init__(self, resource_type: str):
        self.resource_type = resource_type


class FakeRoute:
    def __init__(self, resource_type: str):
        self.request = FakeRouteRequest(resource_type)
        self.aborted = False
        self.continued = False

    async def abort(self) -> None:
        self.aborted = True

    async def continue_(self) -> None:
        self.continued = True


def test_browser_fetcher_non_retained_fetch_writes_storage_and_closes(tmp_path) -> None:
    asyncio.run(_browser_fetcher_non_retained_fetch_writes_storage_and_closes(tmp_path))


async def _browser_fetcher_non_retained_fetch_writes_storage_and_closes(tmp_path) -> None:
    browser = FakeBrowser()
    pw = FakePlaywright()
    fetcher = BrowserFetcher(BrowserFetcherConfig(networkidle_wait_ms=5, user_agent="agent", viewport_width=800))
    fetcher._browser = browser
    fetcher._pw = pw
    storage_path = tmp_path / "state.json"
    session = CrawlSession(
        domain="example.test",
        auth_profile=AuthProfile(profile_id="demo", storage_state_path=str(storage_path)),
        transport=TransportKind.BROWSER,
    )

    response = await fetcher.fetch("https://example.test/page", session=session)

    assert response.status_code == 207
    assert response.final_url == "https://example.test/rendered"
    assert response.html.startswith("<html>")
    assert response.kept_open is False
    assert response.page_ref is None
    assert storage_path.exists()
    assert browser.context_kwargs[0]["user_agent"] == "agent"
    assert browser.context_kwargs[0]["viewport"] == {"width": 800, "height": 720}
    assert browser.contexts[0].routes[0][0] == "**/*"
    assert browser.contexts[0].closed is True
    assert browser.contexts[0].page.closed is True

    await fetcher.aclose()
    assert browser.closed is True
    assert pw.stopped is True


def test_browser_fetcher_keep_page_open_registers_and_aclose_reclaims() -> None:
    asyncio.run(_browser_fetcher_keep_page_open_registers_and_aclose_reclaims())


async def _browser_fetcher_keep_page_open_registers_and_aclose_reclaims() -> None:
    browser = FakeBrowser()
    fetcher = BrowserFetcher(BrowserFetcherConfig(keep_page_open=True, max_open_pages=2))
    fetcher._browser = browser

    response = await fetcher.fetch("https://example.test/page", owner_run_id="run_1")

    assert response.kept_open is True
    assert response.page_ref is not None
    assert response.context_ref is not None
    assert browser.contexts[0].closed is False
    assert browser.contexts[0].page.closed is False

    handle = await fetcher.page_registry.get(response.page_ref)
    assert handle is not None
    assert handle.owner_run_id == "run_1"

    await fetcher.aclose()
    assert browser.contexts[0].closed is True
    assert browser.contexts[0].page.closed is True


def test_browser_page_registry_ttl_lru_and_close() -> None:
    asyncio.run(_browser_page_registry_ttl_lru_and_close())


async def _browser_page_registry_ttl_lru_and_close() -> None:
    registry = BrowserPageRegistry(max_open_pages=1, default_ttl_s=600)
    first_context = FakeContext(FakePage("https://example.test/one"))
    first = await registry.register(
        page=first_context.page,
        context=first_context,
        url="https://example.test/one",
        final_url="https://example.test/one",
    )
    await asyncio.sleep(0)
    second_context = FakeContext(FakePage("https://example.test/two"))
    second = await registry.register(
        page=second_context.page,
        context=second_context,
        url="https://example.test/two",
        final_url="https://example.test/two",
    )

    assert await registry.get(first.page_ref) is None
    assert first_context.closed is True
    assert await registry.get(second.page_ref) is not None

    second_handle = await registry.get(second.page_ref)
    assert second_handle is not None
    second_handle.last_accessed_at = time.time() - 100
    second_handle.ttl_s = 1
    assert await registry.sweep_expired() == 1
    assert second_context.closed is True


def test_browser_route_handler_blocks_only_configured_resource_types() -> None:
    asyncio.run(_browser_route_handler_blocks_only_configured_resource_types())


async def _browser_route_handler_blocks_only_configured_resource_types() -> None:
    fetcher = BrowserFetcher(BrowserFetcherConfig(block_resource_types=("image",)))
    image_route = FakeRoute("image")
    script_route = FakeRoute("script")

    await fetcher._route_handler(image_route)
    await fetcher._route_handler(script_route)

    assert image_route.aborted is True
    assert image_route.continued is False
    assert script_route.aborted is False
    assert script_route.continued is True


def test_hybrid_fetcher_adapts_browser_response() -> None:
    asyncio.run(_hybrid_fetcher_adapts_browser_response())


async def _hybrid_fetcher_adapts_browser_response() -> None:
    browser = FakeBrowser()
    browser_fetcher = BrowserFetcher(BrowserFetcherConfig())
    browser_fetcher._browser = browser
    hybrid = HybridFetcher(browser_fetcher=browser_fetcher)
    plan = CrawlPlan(transport=TransportKind.BROWSER, extract_kind=ExtractKind.UNIVERSAL)

    payload = await hybrid.fetch("https://example.test/page", plan=plan)

    assert payload.meta.transport == TransportKind.BROWSER
    assert payload.meta.status_code == 207
    assert payload.html is not None
    assert b"Rendered by fake browser" in (payload.raw_bytes or b"")
    await browser_fetcher.aclose()
