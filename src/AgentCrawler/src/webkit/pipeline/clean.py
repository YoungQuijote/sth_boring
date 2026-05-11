from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from ..models import Chunk, Document


@dataclass
class Cleaner:
    """Normalize text and produce chunks (paragraph-oriented)."""

    max_chunk_chars: int = 1200
    min_chunk_chars: int = 200

    def clean_text(self, text: str) -> str:
        # normalize whitespace, keep paragraph breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # collapse spaces
        text = re.sub(r"[ \t]+", " ", text)
        # trim lines
        lines = [ln.strip() for ln in text.split("\n")]
        # drop empty streaks down to at most one blank line
        out = []
        blank = False
        for ln in lines:
            if not ln:
                if not blank:
                    out.append("")
                blank = True
            else:
                out.append(ln)
                blank = False
        cleaned = "\n".join(out).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    def chunk(self, doc: Document) -> List[Chunk]:
        cleaned = self.clean_text(doc.text)
        paras = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

        chunks: List[Chunk] = []
        buf = ""
        order = 0

        def flush_buf():
            nonlocal buf, order
            if not buf.strip():
                return
            chunks.append(Chunk(
                text=buf.strip(),
                order=order,
                source_url=doc.url,
                title=doc.title,
                meta={},
            ))
            order += 1
            buf = ""

        for p in paras:
            if len(p) > self.max_chunk_chars:
                # hard split huge paragraph
                start = 0
                while start < len(p):
                    part = p[start:start + self.max_chunk_chars]
                    chunks.append(Chunk(text=part.strip(), order=order, source_url=doc.url, title=doc.title))
                    order += 1
                    start += self.max_chunk_chars
                continue

            if not buf:
                buf = p
            elif len(buf) + 2 + len(p) <= self.max_chunk_chars:
                buf = buf + "\n\n" + p
            else:
                flush_buf()
                buf = p

        flush_buf()

        # merge tiny chunks
        merged: List[Chunk] = []
        tmp = ""
        tmp_order = 0
        for ch in chunks:
            if len(ch.text) < self.min_chunk_chars:
                if not tmp:
                    tmp = ch.text
                    tmp_order = ch.order
                else:
                    tmp += "\n\n" + ch.text
            else:
                if tmp:
                    merged.append(Chunk(text=tmp.strip(), order=tmp_order, source_url=doc.url, title=doc.title))
                    tmp = ""
                merged.append(ch)
        if tmp:
            merged.append(Chunk(text=tmp.strip(), order=tmp_order, source_url=doc.url, title=doc.title))

        # re-number order
        for i, ch in enumerate(merged):
            ch.order = i
        doc.text = cleaned
        doc.chunks = merged
        return merged
