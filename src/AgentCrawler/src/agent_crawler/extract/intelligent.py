from __future__ import annotations

from dataclasses import dataclass

from webkit.models import Document


@dataclass
class IntelligentExtractor:
    llm_client: object | None = None

    async def extract(self, html: str, *, url: str, query: str | None = None) -> Document:
        raise NotImplementedError("LLM-based intelligent extraction is a placeholder for a later implementation.")
