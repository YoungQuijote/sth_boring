from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from webkit.models import Document


class SiteAdapter(Protocol):
    name: str

    def can_handle(self, url: str) -> bool: ...

    def extract(self, html: str, *, url: str) -> Document: ...


@dataclass
class SiteAdapterRegistry:
    _adapters: dict[str, SiteAdapter] = field(default_factory=dict)

    def register(self, adapter: SiteAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str | None) -> SiteAdapter | None:
        if name is None:
            return None
        return self._adapters.get(name)

    def resolve(self, url: str, name: str | None = None) -> SiteAdapter | None:
        adapter = self.get(name)
        if adapter is not None:
            return adapter
        for candidate in self._adapters.values():
            if candidate.can_handle(url):
                return candidate
        return None
