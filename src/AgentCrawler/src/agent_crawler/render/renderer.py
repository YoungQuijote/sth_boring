from __future__ import annotations

from dataclasses import dataclass

from agent_crawler.models import RenderMode
from webkit.models import Document


@dataclass
class Renderer:
    max_links: int = 20
    max_chunks: int = 8

    def render(self, doc: Document, *, mode: RenderMode = RenderMode.PLAIN) -> str:
        if mode == RenderMode.PLAIN:
            return self._plain(doc)
        if mode == RenderMode.STRUCTURED:
            return self._structured(doc)
        if mode == RenderMode.ADAPTER:
            return self._structured(doc)
        if mode == RenderMode.LLM:
            raise NotImplementedError("LLM rendering is a placeholder for a later implementation.")
        return self._plain(doc)

    def _plain(self, doc: Document) -> str:
        parts: list[str] = []
        if doc.title:
            parts.append(f"# {doc.title}")
        parts.append(doc.text.strip())
        if doc.links:
            parts.append("\nLinks:\n" + "\n".join(f"- {link}" for link in doc.links[: self.max_links]))
        return "\n\n".join(part for part in parts if part.strip())

    def _structured(self, doc: Document) -> str:
        parts = [f"# {doc.title or doc.url}", "", "## Key chunks"]
        chunks = doc.chunks[: self.max_chunks]
        if not chunks:
            parts.append(doc.text.strip())
        for idx, chunk in enumerate(chunks, start=1):
            parts.append(f"\n### Chunk {idx} score={chunk.score:.4f}\n{chunk.text.strip()}")
        if doc.links:
            parts.append("\n## Links")
            parts.extend(f"- {link}" for link in doc.links[: self.max_links])
        return "\n".join(parts).strip()
