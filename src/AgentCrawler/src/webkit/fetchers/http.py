from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from ..models import FetchResponse

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_backoff_s: float = 0.6
    max_backoff_s: float = 8.0
    jitter_s: float = 0.25

    def backoff(self, attempt: int) -> float:
        # attempt: 1..max_attempts-1 (since attempt 0 is the first request)
        exp = min(self.max_backoff_s, self.base_backoff_s * (2 ** (attempt - 1)))
        return exp + random.uniform(0, self.jitter_s)


class HostLimiter:
    """Per-host concurrency + minimum interval between request starts."""

    def __init__(self, *, max_concurrency_per_host: int = 2, min_interval_s: float = 0.4):
        self._max_conc = max_concurrency_per_host
        self._min_interval = min_interval_s
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._next_time: Dict[str, float] = {}

    def _get(self, host: str) -> Tuple[asyncio.Semaphore, asyncio.Lock]:
        if host not in self._semaphores:
            self._semaphores[host] = asyncio.Semaphore(self._max_conc)
            self._locks[host] = asyncio.Lock()
            self._next_time[host] = 0.0
        return self._semaphores[host], self._locks[host]

    async def __aenter_host(self, host: str):
        sem, lock = self._get(host)
        await sem.acquire()
        # ensure min-interval between request starts
        async with lock:
            now = time.monotonic()
            wait = self._next_time[host] - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_time[host] = time.monotonic() + self._min_interval

    async def __aexit_host(self, host: str):
        sem, _ = self._get(host)
        sem.release()

    def guard(self, host: str):
        limiter = self

        class _Guard:
            async def __aenter__(self):
                await limiter.__aenter_host(host)

            async def __aexit__(self, exc_type, exc, tb):
                await limiter.__aexit_host(host)

        return _Guard()


class DiskCache:
    """A tiny disk cache for GET responses, with optional conditional revalidation.

    Stores:
      - body: <key>.bin
      - meta: <key>.json (status, headers subset, final_url, fetched_at)
    """

    def __init__(self, cache_dir: str = ".webcache", *, ttl_s: float = 3600.0):
        self.cache_dir = cache_dir
        self.ttl_s = ttl_s
        os.makedirs(cache_dir, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _paths(self, key: str) -> Tuple[str, str]:
        return (
            os.path.join(self.cache_dir, f"{key}.bin"),
            os.path.join(self.cache_dir, f"{key}.json"),
        )

    def load(self, url: str) -> Optional[Tuple[bytes, dict]]:
        key = self._key(url)
        body_path, meta_path = self._paths(key)
        if not (os.path.exists(body_path) and os.path.exists(meta_path)):
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            fetched_at = meta.get("fetched_at_epoch", 0.0)
            if self.ttl_s > 0 and (time.time() - fetched_at) > self.ttl_s:
                # stale, but still usable for conditional requests (caller decides)
                meta["_stale"] = True
            with open(body_path, "rb") as f:
                body = f.read()
            return body, meta
        except Exception:
            return None

    def save(self, url: str, body: bytes, meta: dict) -> None:
        key = self._key(url)
        body_path, meta_path = self._paths(key)
        meta = dict(meta)
        meta["fetched_at_epoch"] = time.time()
        tmp_body = body_path + ".tmp"
        tmp_meta = meta_path + ".tmp"
        with open(tmp_body, "wb") as f:
            f.write(body)
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        os.replace(tmp_body, body_path)
        os.replace(tmp_meta, meta_path)


class HttpFetcher:
    def __init__(
        self,
        *,
        timeout_s: float = 20.0,
        headers: Optional[Dict[str, str]] = None,
        limiter: Optional[HostLimiter] = None,
        cache: Optional[DiskCache] = None,
        retry: Optional[RetryPolicy] = None,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ):
        self._timeout = httpx.Timeout(timeout_s)
        self._headers = headers or {
            "User-Agent": "web-agent-mvp/0.1 (+https://example.invalid)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self._limiter = limiter or HostLimiter()
        self._cache = cache or DiskCache()
        self._retry = retry or RetryPolicy()
        self._follow_redirects = follow_redirects
        self._verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "HttpFetcher":
        self._client = httpx.AsyncClient(
            headers=self._headers,
            timeout=self._timeout,
            follow_redirects=self._follow_redirects,
            verify=self._verify_ssl,
            http2=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str, *, method: str = "GET", headers: Optional[Dict[str, str]] = None) -> FetchResponse:
        if method.upper() != "GET":
            raise ValueError("MVP cache/revalidation only supports GET")

        parsed = urlparse(url)
        host = parsed.netloc.lower() or "unknown"

        cached = self._cache.load(url) if self._cache else None
        cached_body = None
        cached_meta = None
        conditional_headers: Dict[str, str] = {}
        if cached:
            cached_body, cached_meta = cached
            # If stale, try conditional GET if we can.
            if cached_meta.get("_stale"):
                etag = (cached_meta.get("headers") or {}).get("etag")
                last_mod = (cached_meta.get("headers") or {}).get("last-modified")
                if etag:
                    conditional_headers["If-None-Match"] = etag
                if last_mod:
                    conditional_headers["If-Modified-Since"] = last_mod
            else:
                # fresh cache hit
                return FetchResponse(
                    url=url,
                    final_url=cached_meta.get("final_url", url),
                    status_code=cached_meta.get("status_code", 200),
                    headers=cached_meta.get("headers", {}),
                    content=cached_body,
                    encoding=cached_meta.get("encoding"),
                    fetched_at=datetime.fromtimestamp(cached_meta.get("fetched_at_epoch", time.time()), tz=timezone.utc).replace(tzinfo=None),
                )

        if self._client is None:
            # allow use without context manager (less efficient)
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=self._timeout,
                follow_redirects=self._follow_redirects,
                verify=self._verify_ssl,
                http2=True,
            )

        req_headers = dict(headers or {})
        req_headers.update(conditional_headers)

        last_exc: Optional[Exception] = None
        for attempt in range(1, self._retry.max_attempts + 1):
            try:
                async with self._limiter.guard(host):
                    resp = await self._client.get(url, headers=req_headers)
                status = resp.status_code

                if status == 304 and cached_body is not None and cached_meta is not None:
                    # Not modified: use cached body, but refresh fetched_at
                    cached_meta["_stale"] = False
                    self._cache.save(url, cached_body, cached_meta)
                    return FetchResponse(
                        url=url,
                        final_url=str(resp.url),
                        status_code=200,
                        headers={k.lower(): v for k, v in (cached_meta.get("headers") or {}).items()},
                        content=cached_body,
                        encoding=cached_meta.get("encoding"),
                        fetched_at=datetime.utcnow(),
                    )

                if status in RETRYABLE_STATUSES and attempt < self._retry.max_attempts:
                    await asyncio.sleep(self._retry.backoff(attempt))
                    continue

                content = resp.content
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                encoding = resp.encoding

                meta = {
                    "final_url": str(resp.url),
                    "status_code": status,
                    "headers": {k: hdrs.get(k) for k in ["content-type", "etag", "last-modified"] if hdrs.get(k)},
                    "encoding": encoding,
                }
                if self._cache and status == 200 and content:
                    self._cache.save(url, content, meta)

                return FetchResponse(
                    url=url,
                    final_url=str(resp.url),
                    status_code=status,
                    headers=hdrs,
                    content=content,
                    encoding=encoding,
                    fetched_at=datetime.utcnow(),
                )

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                last_exc = e
                if attempt >= self._retry.max_attempts:
                    break
                await asyncio.sleep(self._retry.backoff(attempt))
            except Exception as e:
                last_exc = e
                break

        raise RuntimeError(f"Fetch failed for {url}: {last_exc}") from last_exc
