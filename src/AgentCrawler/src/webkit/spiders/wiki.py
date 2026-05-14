from __future__ import annotations

from dataclasses import dataclass

from ..extractors.html import WikiExtractor
from .base import Spider


@dataclass
class WikiSpider(Spider):
    """Example adapter. You can add more site spiders similarly."""

    def __init__(self, fetcher, cleaner, reranker):
        super().__init__(fetcher=fetcher, extractor=WikiExtractor(), cleaner=cleaner, reranker=reranker)
