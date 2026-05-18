from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass

from agent_crawler.models import CrawlPlan, CrawlRequest, CrawlResultBundle


@dataclass
class _CacheEntry:
    bundle: CrawlResultBundle
    expires_at: float


class ResultCache:
    def __init__(self, *, ttl_s: float = 600.0, max_entries: int = 128):
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self._items: OrderedDict[str, _CacheEntry] = OrderedDict()

    def make_key(self, request: CrawlRequest, plan: CrawlPlan) -> str:
        return "|".join(
            [
                request.url,
                request.query or "",
                request.auth_profile_id,
                plan.transport.value,
                plan.extract_kind.value,
                plan.adapter_name or "",
            ]
        )

    def get(self, key: str) -> CrawlResultBundle | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return entry.bundle

    def put(self, key: str, bundle: CrawlResultBundle, *, ttl_s: float | None = None) -> None:
        ttl = self.ttl_s if ttl_s is None else ttl_s
        self._items[key] = _CacheEntry(bundle=bundle, expires_at=time.time() + ttl)
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
