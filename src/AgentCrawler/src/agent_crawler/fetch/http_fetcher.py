from __future__ import annotations

import importlib
from typing import Any


def _legacy(name: str) -> type[Any]:
    module = importlib.import_module("webkit.fetchers.http")
    return getattr(module, name)


class HttpFetcher:
    def __init__(self, *args: Any, **kwargs: Any):
        self._impl = _legacy("HttpFetcher")(*args, **kwargs)

    async def __aenter__(self) -> "HttpFetcher":
        await self._impl.__aenter__()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self._impl.__aexit__(exc_type, exc, tb)

    async def fetch(self, *args: Any, **kwargs: Any) -> Any:
        return await self._impl.fetch(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._impl, name)


class HostLimiter:
    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        return _legacy("HostLimiter")(*args, **kwargs)


class DiskCache:
    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        return _legacy("DiskCache")(*args, **kwargs)


class RetryPolicy:
    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        return _legacy("RetryPolicy")(*args, **kwargs)


__all__ = ["DiskCache", "HostLimiter", "HttpFetcher", "RetryPolicy"]
