from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BrowserPageHandle:
    page_ref: str
    context_ref: str
    page: Any
    context: Any
    url: str
    final_url: str
    domain: str | None = None
    auth_profile_id: str | None = None
    owner_run_id: str | None = None
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    ttl_s: int = 600


class BrowserPageRegistry:
    def __init__(self, *, max_open_pages: int = 8, default_ttl_s: int = 600):
        self.max_open_pages = max(1, max_open_pages)
        self.default_ttl_s = default_ttl_s
        self._pages: dict[str, BrowserPageHandle] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        *,
        page: Any,
        context: Any,
        url: str,
        final_url: str,
        domain: str | None = None,
        auth_profile_id: str | None = None,
        owner_run_id: str | None = None,
        ttl_s: int | None = None,
    ) -> BrowserPageHandle:
        async with self._lock:
            await self._sweep_expired_locked()
            handle = BrowserPageHandle(
                page_ref=f"page_{uuid.uuid4().hex}",
                context_ref=f"ctx_{uuid.uuid4().hex}",
                page=page,
                context=context,
                url=url,
                final_url=final_url,
                domain=domain,
                auth_profile_id=auth_profile_id,
                owner_run_id=owner_run_id,
                ttl_s=self.default_ttl_s if ttl_s is None else ttl_s,
            )
            self._pages[handle.page_ref] = handle
            await self._evict_if_needed_locked()
            return handle

    async def get(self, page_ref: str) -> BrowserPageHandle | None:
        async with self._lock:
            handle = self._pages.get(page_ref)
            if handle is None:
                return None
            if self._is_expired(handle):
                self._pages.pop(page_ref, None)
                await self._close_handle(handle)
                return None
            handle.last_accessed_at = time.time()
            return handle

    async def close(self, page_ref: str) -> bool:
        async with self._lock:
            handle = self._pages.pop(page_ref, None)
            if handle is None:
                return False
            await self._close_handle(handle)
            return True

    async def sweep_expired(self) -> int:
        async with self._lock:
            return await self._sweep_expired_locked()

    async def close_all(self) -> None:
        async with self._lock:
            handles = list(self._pages.values())
            self._pages.clear()
            for handle in handles:
                await self._close_handle(handle)

    def __len__(self) -> int:
        return len(self._pages)

    async def _sweep_expired_locked(self) -> int:
        expired = [page_ref for page_ref, handle in self._pages.items() if self._is_expired(handle)]
        for page_ref in expired:
            handle = self._pages.pop(page_ref, None)
            if handle is not None:
                await self._close_handle(handle)
        return len(expired)

    async def _evict_if_needed_locked(self) -> None:
        overflow = len(self._pages) - self.max_open_pages
        if overflow <= 0:
            return
        page_refs = [
            page_ref
            for page_ref, _ in sorted(self._pages.items(), key=lambda item: item[1].last_accessed_at)[:overflow]
        ]
        for page_ref in page_refs:
            handle = self._pages.pop(page_ref, None)
            if handle is not None:
                await self._close_handle(handle)

    def _is_expired(self, handle: BrowserPageHandle) -> bool:
        return handle.ttl_s > 0 and (time.time() - handle.last_accessed_at) > handle.ttl_s

    async def _close_handle(self, handle: BrowserPageHandle) -> None:
        try:
            await handle.page.close()
        except Exception:
            pass
        try:
            await handle.context.close()
        except Exception:
            pass
