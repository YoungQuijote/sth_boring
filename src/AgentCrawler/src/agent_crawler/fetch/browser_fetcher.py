from __future__ import annotations

import asyncio
import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .browser_registry import BrowserPageRegistry

_PLAYWRIGHT_INSTALL_MESSAGE = (
    "BrowserFetcher requires playwright. Please install playwright and run playwright install chromium."
)


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


class BrowserFetcher:
    def __init__(
        self,
        config: BrowserFetcherConfig | None = None,
        page_registry: BrowserPageRegistry | None = None,
    ) -> None:
        self.config = config or BrowserFetcherConfig()
        if self.config.context_strategy != "per_fetch":
            raise ValueError("BrowserFetcher v1 only supports context_strategy='per_fetch'")
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

                html = await page.content()
                final_url = page.url
                status_code = response.status if response is not None else 0
                headers = dict(response.headers) if response is not None and response.headers is not None else {}

                if storage_state_path is not None:
                    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
                    await context.storage_state(path=str(storage_state_path))

                elapsed_ms = (time.monotonic() - started) * 1000.0
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
                    return BrowserFetchResponse(
                        url=url,
                        final_url=final_url,
                        status_code=status_code,
                        html=html,
                        headers=headers,
                        elapsed_ms=elapsed_ms,
                        page_ref=handle.page_ref,
                        context_ref=handle.context_ref,
                        kept_open=True,
                    )

                return BrowserFetchResponse(
                    url=url,
                    final_url=final_url,
                    status_code=status_code,
                    html=html,
                    headers=headers,
                    elapsed_ms=elapsed_ms,
                    kept_open=False,
                )
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
