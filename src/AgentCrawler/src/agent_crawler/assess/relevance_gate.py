from __future__ import annotations

from dataclasses import dataclass

from agent_crawler.models import RelevanceResult
from webkit.models import Document


@dataclass
class RelevanceGate:
    llm_client: object | None = None

    async def check(self, doc: Document, *, query: str | None = None) -> RelevanceResult | None:
        if not query:
            return None
        raise NotImplementedError("LLM relevance gate is a placeholder and is disabled by default.")
