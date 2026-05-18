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

class FakeRedirectRequest:
    def __init__(self, url: str, redirected_from=None):
        self.url = url
        self.redirected_from = redirected_from


class FakeRedirectResponse(FakeResponse):
    def __init__(self):
        first = FakeRedirectRequest("https://example.test/private")
        second = FakeRedirectRequest("https://example.test/login?next=https%3A//example.test/private", first)
        self.request = second


class LoginPage(FakePage):
    def __init__(self):
        super().__init__("https://example.test/login?next=https%3A//example.test/private")

    async def goto(self, url: str, *, wait_until: str, timeout: int):
        self.goto_calls.append((url, wait_until, timeout))
        return FakeRedirectResponse()

    async def content(self) -> str:
        return """
        <html><body>
          <form action="/login"><input name="email"><input type="password" name="password"></form>
          <p>Sign in to continue to https://example.test/private</p>
        </body></html>
        """


class LoginBrowser(FakeBrowser):
    async def new_context(self, **kwargs) -> FakeContext:
        page = LoginPage()
        context = FakeContext(page)
        self.contexts.append(context)
        self.context_kwargs.append(kwargs)
        return context


class InteractiveLoginPage(FakePage):
    def __init__(self):
        super().__init__("https://example.test/login?next=https%3A//example.test/private")
        self.content_calls = 0

    @property
    def url(self) -> str:
        if self.content_calls >= 1:
            return "https://example.test/private"
        return "https://example.test/login?next=https%3A//example.test/private"

    @url.setter
    def url(self, value: str) -> None:
        self._initial_url = value

    async def content(self) -> str:
        self.content_calls += 1
        if self.content_calls == 1:
            return """
            <html><body>
              <form><input type="password"></form>
              <p>Login for https://example.test/private</p>
            </body></html>
            """
        return "<html><body><main>Private dashboard content with many useful words and no login form.</main></body></html>"


class InteractiveLoginBrowser(FakeBrowser):
    async def new_context(self, **kwargs) -> FakeContext:
        page = InteractiveLoginPage()
        context = FakeContext(page)
        self.contexts.append(context)
        self.context_kwargs.append(kwargs)
        return context


def test_auth_gate_detects_login_with_redirect_and_password() -> None:
    from agent_crawler.fetch import AuthGate, BrowserAuthConfig

    gate = AuthGate(BrowserAuthConfig())
    result = gate.detect(
        source_url="https://example.test/private",
        final_url="https://example.test/login?next=https%3A//example.test/private",
        html='<form><input type="password">Sign in</form>',
        redirect_chain=["https://example.test/private", "https://example.test/login"],
    )

    assert result.login_required is True
    assert result.confidence >= 0.45
    assert result.has_password_input is True
    assert result.has_redirect_history is True
    assert "login" in result.matched_url_keywords


def test_browser_fetcher_auth_required_without_interactive_login() -> None:
    asyncio.run(_browser_fetcher_auth_required_without_interactive_login())


async def _browser_fetcher_auth_required_without_interactive_login() -> None:
    browser = LoginBrowser()
    fetcher = BrowserFetcher(BrowserFetcherConfig())
    fetcher._browser = browser

    response = await fetcher.fetch("https://example.test/private")

    assert response.auth_required is True
    assert response.auth_confidence >= 0.45
    assert response.interactive_login_used is False
    assert response.interactive_login_success is None
    assert response.before_login_url == response.final_url
    assert response.before_login_density_score is not None
    assert response.redirect_chain == [
        "https://example.test/private",
        "https://example.test/login?next=https%3A//example.test/private",
    ]
    assert browser.contexts[0].closed is True


def test_browser_fetcher_rejects_headless_interactive_login() -> None:
    from agent_crawler.fetch import BrowserAuthConfig

    try:
        BrowserFetcher(BrowserFetcherConfig(headless=True, auth=BrowserAuthConfig(interactive_login=True)))
    except ValueError as exc:
        assert "interactive_login requires headed browser" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_browser_fetcher_interactive_login_success_updates_html_and_state(tmp_path) -> None:
    asyncio.run(_browser_fetcher_interactive_login_success_updates_html_and_state(tmp_path))


async def _browser_fetcher_interactive_login_success_updates_html_and_state(tmp_path) -> None:
    from agent_crawler.fetch import BrowserAuthConfig

    browser = InteractiveLoginBrowser()
    storage_path = tmp_path / "interactive_state.json"
    session = CrawlSession(
        domain="example.test",
        auth_profile=AuthProfile(profile_id="demo", storage_state_path=str(storage_path)),
        transport=TransportKind.BROWSER,
    )
    fetcher = BrowserFetcher(
        BrowserFetcherConfig(
            headless=False,
            auth=BrowserAuthConfig(interactive_login=True, login_wait_timeout_ms=500, login_poll_interval_ms=10),
        )
    )
    fetcher._browser = browser

    response = await fetcher.fetch("https://example.test/private", session=session)

    assert response.auth_required is True
    assert response.interactive_login_used is True
    assert response.interactive_login_success is True
    assert response.login_wait_reason in {"density_improved_not_login", "source_url_returned_not_login"}
    assert response.final_url == "https://example.test/private"
    assert "Private dashboard content" in response.html
    assert response.after_login_density_score is not None
    assert response.before_login_density_score is not None
    assert response.after_login_density_score > response.before_login_density_score
    assert storage_path.exists()
    assert browser.contexts[0].closed is True

class TransientContentPage(FakePage):
    def __init__(
        self,
        failures: int = 1,
        message: str = "Page.content: Unable to retrieve content because the page is navigating and changing the content.",
    ):
        super().__init__()
        self.failures = failures
        self.message = message
        self.wait_load_state_calls = []

    async def content(self) -> str:
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError(self.message)
        return "<html><body>stable content</body></html>"

    async def wait_for_load_state(self, state: str, *, timeout: int):
        self.wait_load_state_calls.append((state, timeout))


class NonTransientContentPage(FakePage):
    async def content(self) -> str:
        raise RuntimeError("Page.content: parser exploded in a non-retryable way")


def test_safe_page_content_retries_transient_navigation_error() -> None:
    asyncio.run(_safe_page_content_retries_transient_navigation_error())


async def _safe_page_content_retries_transient_navigation_error() -> None:
    fetcher = BrowserFetcher(BrowserFetcherConfig())
    page = TransientContentPage(failures=2)

    html = await fetcher._safe_page_content(page, attempts=3, retry_interval_ms=0, wait_load_state_ms=7)

    assert html == "<html><body>stable content</body></html>"
    assert page.wait_load_state_calls == [("domcontentloaded", 7), ("domcontentloaded", 7)]


def test_safe_page_content_returns_none_after_transient_retries_exhausted() -> None:
    asyncio.run(_safe_page_content_returns_none_after_transient_retries_exhausted())


async def _safe_page_content_returns_none_after_transient_retries_exhausted() -> None:
    fetcher = BrowserFetcher(BrowserFetcherConfig())
    page = TransientContentPage(failures=3, message="Execution context was destroyed, most likely because of a navigation")

    html = await fetcher._safe_page_content(page, attempts=2, retry_interval_ms=0, wait_load_state_ms=0)

    assert html is None


def test_safe_page_content_reraises_non_transient_errors() -> None:
    asyncio.run(_safe_page_content_reraises_non_transient_errors())


async def _safe_page_content_reraises_non_transient_errors() -> None:
    fetcher = BrowserFetcher(BrowserFetcherConfig())
    page = NonTransientContentPage()

    try:
        await fetcher._safe_page_content(page, attempts=2, retry_interval_ms=0)
    except RuntimeError as exc:
        assert "non-retryable" in str(exc)
    else:
        raise AssertionError("expected non-transient error to be raised")
