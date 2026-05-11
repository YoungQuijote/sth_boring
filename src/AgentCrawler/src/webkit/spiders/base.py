from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..fetchers.http import HttpFetcher
from ..extractors.html import HtmlExtractor
from ..pipeline.clean import Cleaner
from ..pipeline.rerank import SimpleReranker
from ..models import Document


@dataclass
class Spider:
    fetcher: HttpFetcher
    extractor: HtmlExtractor
    cleaner: Cleaner
    reranker: SimpleReranker

    async def crawl(self, url: str, *, query: Optional[str] = None) -> Document:
        resp = await self.fetcher.fetch(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"Bad status {resp.status_code} for {url}")

        doc = self.extractor.extract(resp.text(), url=url)
        self.cleaner.chunk(doc)
        doc.chunks = self.reranker.rank(doc.chunks, query=query)
        return doc
