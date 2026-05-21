from __future__ import annotations

import asyncio
import importlib.util
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .auth_gate import AuthDetectionResult, AuthGate, BrowserAuthConfig, LoginWaitResult, now_ms
from .browser_registry import BrowserPageRegistry

_PLAYWRIGHT_INSTALL_MESSAGE = (
    "BrowserFetcher requires playwright. Please install playwright and run playwright install chromium."
)
_INTERACTIVE_LOGIN_HEADLESS_ERROR = "interactive_login requires headed browser. Please set headless=False."


@dataclass(slots=True)
class BrowserFetcherConfig:
    browser_name: str = "chromium"
    headless: bool = True
    keep_page_open: bool = False
    max_open_pages: int = 8
    page_ttl_s: int = 600
    max_concurrency: int = 2
    nav_timeout_ms: int = 30_000
    wait_until: str = "domcontentloaded"
    networkidle_wait_ms: int = 2_000
    block_resource_types: tuple[str, ...] = ("image", "media", "font")
    context_strategy: str = "per_fetch"
    user_agent: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    ignore_https_errors: bool = False
    auth: BrowserAuthConfig = field(default_factory=BrowserAuthConfig)


@dataclass(slots=True)
class BrowserFetchResponse:
    url: str
    final_url: str
    status_code: int
    html: str
    headers: dict[str, str]
    elapsed_ms: float
    transport: str = "browser"
    page_ref: str | None = None
    context_ref: str | None = None
    screenshot_path: str | None = None
    kept_open: bool = False
    redirect_chain: list[str] = field(default_factory=list)
    auth_required: bool = False
    auth_confidence: float = 0.0
    auth_reason: str | None = None
    interactive_login_used: bool = False
    interactive_login_success: bool | None = None
    login_wait_reason: str | None = None
    before_login_url: str | None = None
    after_login_url: str | None = None
    before_login_density_score: float | None = None
    after_login_density_score: float | None = None
    storage_state_used: bool = False
    storage_state_saved: bool = False


class BrowserFetcher:
    def __init__(
        self,
        config: BrowserFetcherConfig | None = None,
        page_registry: BrowserPageRegistry | None = None,
        auth_gate: AuthGate | None = None,
    ) -> None:
        self.config = config or BrowserFetcherConfig()
        if self.config.context_strategy != "per_fetch":
            raise ValueError("BrowserFetcher v1 only supports context_strategy='per_fetch'")
        if self.config.auth.interactive_login and self.config.headless:
            raise ValueError(_INTERACTIVE_LOGIN_HEADLESS_ERROR)
        self.auth_gate = auth_gate or AuthGate(self.config.auth)
        self.page_registry = page_registry or BrowserPageRegistry(
            max_open_pages=self.config.max_open_pages,
            default_ttl_s=self.config.page_ttl_s,
        )
        self._sem = asyncio.Semaphore(max(1, self.config.max_concurrency))
        self._init_lock = asyncio.Lock()
        self._pw: Any | None = None
        self._browser: Any | None = None
        self._closed = False

    async def __aenter__(self) -> BrowserFetcher:
        await self._ensure_browser()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.aclose()

    async def fetch(
        self,
        url: str,
        *,
        session: object | None = None,
        keep_page_open: bool | None = None,
        owner_run_id: str | None = None,
        interactive_login: bool | None = None,
    ) -> BrowserFetchResponse:
        if self._closed:
            raise RuntimeError("BrowserFetcher is closed")

        should_keep_open = self.config.keep_page_open if keep_page_open is None else keep_page_open
        started = time.monotonic()
        context: Any | None = None
        page: Any | None = None
        kept_open = False

        async with self._sem:
            await self._ensure_browser()
            storage_state_path = self._resolve_storage_state_path(session)
            auth_profile_id = self._resolve_auth_profile_id(session)
            context_kwargs = self._build_context_kwargs(storage_state_path)

            try:
                context = await self._browser.new_context(**context_kwargs)
                if self.config.block_resource_types:
                    await context.route("**/*", self._route_handler)
                page = await context.new_page()
            except Exception as exc:
                await self._close_page_and_context(page, context)
                raise RuntimeError(f"Browser context/page creation failed for {url}: {exc}") from exc

            try:
                try:
                    response = await page.goto(
                        url,
                        wait_until=self.config.wait_until,
                        timeout=self.config.nav_timeout_ms,
                    )
                except Exception as exc:
                    raise RuntimeError(f"Browser navigation timeout for {url}: {exc}") from exc

                if self.config.networkidle_wait_ms > 0:
                    try:
                        await page.wait_for_load_state("networkidle", timeout=self.config.networkidle_wait_ms)
                    except Exception:
                        pass

                html = await self._safe_page_content(page)
                if html is None:
                    raise RuntimeError(f"Page content unavailable for {url}: page kept navigating or closed")
                final_url = page.url
                status_code = response.status if response is not None else 0
                headers = dict(response.headers) if response is not None and response.headers is not None else {}
                redirect_chain = self._build_redirect_chain(response)
                detection = self.auth_gate.detect(
                    source_url=url,
                    final_url=final_url,
                    html=html,
                    redirect_chain=redirect_chain,
                )
                login_wait_result: LoginWaitResult | None = None
                auth_reason = detection.reason
                interactive_login_used = False

                use_interactive_login = self.config.auth.interactive_login if interactive_login is None else interactive_login
                if use_interactive_login and self.config.headless:
                    raise ValueError(_INTERACTIVE_LOGIN_HEADLESS_ERROR)

                if detection.login_required and use_interactive_login:
                    interactive_login_used = True
                    login_wait_result = await self._wait_for_interactive_login(
                        page=page,
                        source_url=url,
                        before_url=final_url,
                        before_html=html,
                        before_density_score=detection.text_density_score,
                    )
                    auth_reason = f"{detection.reason};{login_wait_result.reason}"
                    if login_wait_result.success:
                        final_html = await self._safe_page_content(page, attempts=8, retry_interval_ms=500)
                        if final_html is not None:
                            html = final_html
                            final_url = page.url
                    else:
                        # Return the latest visible login/SSO page rather than stale pre-wait HTML.
                        latest_html = await self._safe_page_content(page, attempts=8, retry_interval_ms=500)
                        if latest_html is not None:
                            html = latest_html
                            final_url = page.url

                storage_state_used = storage_state_path is not None and storage_state_path.exists()
                storage_state_reason = await self._try_save_storage_state(context, storage_state_path)
                storage_state_saved = storage_state_reason is None and storage_state_path is not None
                if storage_state_reason:
                    auth_reason = f"{auth_reason};{storage_state_reason}" if auth_reason else storage_state_reason

                elapsed_ms = (time.monotonic() - started) * 1000.0
                response_payload = self._make_response(
                    url=url,
                    final_url=final_url,
                    status_code=status_code,
                    html=html,
                    headers=headers,
                    elapsed_ms=elapsed_ms,
                    redirect_chain=redirect_chain,
                    detection=detection,
                    auth_reason=auth_reason,
                    interactive_login_used=interactive_login_used,
                    login_wait_result=login_wait_result,
                    storage_state_used=storage_state_used,
                    storage_state_saved=storage_state_saved,
                )

                if should_keep_open:
                    handle = await self.page_registry.register(
                        page=page,
                        context=context,
                        url=url,
                        final_url=final_url,
                        domain=urlparse(final_url or url).netloc.lower() or None,
                        auth_profile_id=auth_profile_id,
                        owner_run_id=owner_run_id,
                        ttl_s=self.config.page_ttl_s,
                    )
                    kept_open = True
                    response_payload.page_ref = handle.page_ref
                    response_payload.context_ref = handle.context_ref
                    response_payload.kept_open = True

                return response_payload
            finally:
                if not kept_open:
                    await self._close_page_and_context(page, context)

    async def aclose(self) -> None:
        self._closed = True
        await self.page_registry.close_all()
        if self._browser is not None:
            try:
                await self._browser.close()
            finally:
                self._browser = None
        if self._pw is not None:
            try:
                await self._pw.stop()
            finally:
                self._pw = None

    async def _ensure_browser(self) -> None:
        if self._browser is not None:
            return
        async with self._init_lock:
            if self._browser is not None:
                return
            if importlib.util.find_spec("playwright") is None:
                raise RuntimeError(_PLAYWRIGHT_INSTALL_MESSAGE)

            from playwright.async_api import async_playwright

            try:
                self._pw = await async_playwright().start()
                browser_type = getattr(self._pw, self.config.browser_name, None)
                if browser_type is None:
                    raise ValueError(f"Unsupported browser_name: {self.config.browser_name}")
                self._browser = await browser_type.launch(headless=self.config.headless)
            except Exception as exc:
                if self._pw is not None:
                    try:
                        await self._pw.stop()
                    except Exception:
                        pass
                    self._pw = None
                raise RuntimeError(f"Browser launch failed: {exc}. {_PLAYWRIGHT_INSTALL_MESSAGE}") from exc

    async def _wait_for_interactive_login(
        self,
        *,
        page: Any,
        source_url: str,
        before_url: str,
        before_html: str,
        before_density_score: float,
    ) -> LoginWaitResult:
        started_ms = now_ms()
        deadline_ms = started_ms + self.config.auth.login_wait_timeout_ms
        interval_s = max(self.config.auth.login_poll_interval_ms, 50) / 1000.0
        last_url = before_url
        last_density = before_density_score
        last_html_len = len(before_html or "")

        while now_ms() < deadline_ms:
            current_url = page.url
            current_html = await self._safe_page_content(page)
            if current_html is None:
                await asyncio.sleep(interval_s)
                continue
            current_density = self.auth_gate.compute_text_density_score(current_html)
            last_url = current_url
            last_density = current_density
            last_html_len = len(current_html or "")

            if self.auth_gate.success_url_matches(current_url):
                return self._login_wait_result(
                    True,
                    "success_url_pattern",
                    before_url,
                    current_url,
                    before_density_score,
                    current_density,
                    started_ms,
                    len(current_html),
                )

            if await self._success_selector_matches(page):
                return self._login_wait_result(
                    True,
                    "success_selector",
                    before_url,
                    current_url,
                    before_density_score,
                    current_density,
                    started_ms,
                    len(current_html),
                )

            detection = self.auth_gate.detect(
                source_url=source_url,
                final_url=current_url,
                html=current_html,
                redirect_chain=[],
            )
            source_in_url = self.auth_gate.source_url_in_current_url(source_url, current_url)
            if not detection.login_required and current_density > before_density_score + 0.05:
                return self._login_wait_result(
                    True,
                    "density_improved_not_login",
                    before_url,
                    current_url,
                    before_density_score,
                    current_density,
                    started_ms,
                    len(current_html),
                )
            if source_in_url and not detection.login_required and current_density > before_density_score:
                return self._login_wait_result(
                    True,
                    "source_url_returned_not_login",
                    before_url,
                    current_url,
                    before_density_score,
                    current_density,
                    started_ms,
                    len(current_html),
                )
            await asyncio.sleep(interval_s)

        return self._login_wait_result(
            False,
            "login_wait_timeout",
            before_url,
            last_url,
            before_density_score,
            last_density,
            started_ms,
            last_html_len,
        )

    async def _safe_page_content(
        self,
        page: Any,
        *,
        attempts: int = 5,
        retry_interval_ms: int = 300,
        wait_load_state_ms: int = 1000,
    ) -> str | None:
        attempts = max(1, attempts)
        for attempt in range(1, attempts + 1):
            try:
                return await page.content()
            except Exception as exc:
                if not self._is_transient_page_content_error(exc):
                    raise
                if attempt >= attempts:
                    return None
                if wait_load_state_ms > 0:
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=wait_load_state_ms)
                    except Exception:
                        pass
                await asyncio.sleep(max(0, retry_interval_ms) / 1000.0)
        return None

    def _is_transient_page_content_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        transient_markers = (
            "page is navigating",
            "changing the content",
            "execution context was destroyed",
            "target closed",
            "page closed",
            "browser has been closed",
        )
        return any(marker in message for marker in transient_markers)

    async def _success_selector_matches(self, page: Any) -> bool:
        for selector in self.config.auth.success_selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    return True
            except Exception:
                continue
        return False

    def _login_wait_result(
        self,
        success: bool,
        reason: str,
        before_url: str,
        after_url: str,
        before_density_score: float,
        after_density_score: float,
        started_ms: float,
        final_html_len: int,
    ) -> LoginWaitResult:
        return LoginWaitResult(
            success=success,
            reason=reason,
            before_url=before_url,
            after_url=after_url,
            before_density_score=before_density_score,
            after_density_score=after_density_score,
            waited_ms=max(0.0, now_ms() - started_ms),
            final_html_len=final_html_len,
        )

    def _make_response(
        self,
        *,
        url: str,
        final_url: str,
        status_code: int,
        html: str,
        headers: dict[str, str],
        elapsed_ms: float,
        redirect_chain: list[str],
        detection: AuthDetectionResult,
        auth_reason: str | None,
        interactive_login_used: bool,
        login_wait_result: LoginWaitResult | None,
        storage_state_used: bool,
        storage_state_saved: bool,
    ) -> BrowserFetchResponse:
        return BrowserFetchResponse(
            url=url,
            final_url=final_url,
            status_code=status_code,
            html=html,
            headers=headers,
            elapsed_ms=elapsed_ms,
            redirect_chain=redirect_chain,
            auth_required=detection.login_required,
            auth_confidence=detection.confidence,
            auth_reason=auth_reason,
            interactive_login_used=interactive_login_used,
            interactive_login_success=login_wait_result.success if login_wait_result is not None else None,
            login_wait_reason=login_wait_result.reason if login_wait_result is not None else None,
            before_login_url=detection.final_url if detection.login_required else None,
            after_login_url=login_wait_result.after_url if login_wait_result is not None else None,
            before_login_density_score=detection.text_density_score if detection.login_required else None,
            after_login_density_score=login_wait_result.after_density_score if login_wait_result is not None else None,
            storage_state_used=storage_state_used,
            storage_state_saved=storage_state_saved,
        )

    def _build_redirect_chain(self, response: Any | None) -> list[str]:
        if response is None:
            return []
        chain: list[str] = []
        req = getattr(response, "request", None)
        seen: set[int] = set()
        while req is not None and id(req) not in seen:
            seen.add(id(req))
            req_url = getattr(req, "url", None)
            if req_url:
                chain.append(req_url)
            redirected_from = getattr(req, "redirected_from", None)
            req = redirected_from() if callable(redirected_from) else redirected_from
        chain.reverse()
        return chain

    def _build_context_kwargs(self, storage_state_path: Path | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"ignore_https_errors": self.config.ignore_https_errors}
        if self.config.user_agent is not None:
            kwargs["user_agent"] = self.config.user_agent
        if self.config.viewport_width is not None or self.config.viewport_height is not None:
            kwargs["viewport"] = {
                "width": self.config.viewport_width or 1280,
                "height": self.config.viewport_height or 720,
            }
        if storage_state_path is not None and storage_state_path.exists():
            kwargs["storage_state"] = str(storage_state_path)
        return kwargs

    def _resolve_storage_state_path(self, session: object | None) -> Path | None:
        auth_profile = getattr(session, "auth_profile", None)
        raw_path = getattr(auth_profile, "storage_state_path", None)
        if raw_path is None:
            return None
        return Path(raw_path)

    def _resolve_auth_profile_id(self, session: object | None) -> str | None:
        auth_profile = getattr(session, "auth_profile", None)
        return getattr(auth_profile, "profile_id", None) or getattr(auth_profile, "auth_profile_id", None)

    async def _try_save_storage_state(self, context: Any | None, storage_state_path: Path | None) -> str | None:
        if context is None or storage_state_path is None:
            return None
        try:
            storage_state_path.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(storage_state_path))
            return None
        except Exception as exc:
            return f"storage_state_save_failed:{exc}"

    async def _route_handler(self, route: Any) -> None:
        try:
            request = route.request
            if request.resource_type in self.config.block_resource_types:
                await route.abort()
            else:
                await route.continue_()
        except Exception:
            try:
                await route.continue_()
            except Exception:
                pass

    async def _close_page_and_context(self, page: Any | None, context: Any | None) -> None:
        if page is not None:
            try:
                await page.close()
            except Exception:
                pass
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass
