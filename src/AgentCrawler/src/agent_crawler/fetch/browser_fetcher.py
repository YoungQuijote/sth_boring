from __future__ import annotations

from dataclasses import dataclass

from agent_crawler.models import ErrorType


@dataclass
class BrowserFetchResponse:
    url: str
    final_url: str
    status_code: int
    html: str
    headers: dict[str, str]
    elapsed_ms: float = 0.0


class BrowserFetcher:
    async def fetch(self, url: str, *, session: object | None = None) -> BrowserFetchResponse:
        raise NotImplementedError(
            f"{ErrorType.UNSUPPORTED_TRANSPORT.value}: BrowserFetcher is a placeholder; Playwright integration is planned."
        )
