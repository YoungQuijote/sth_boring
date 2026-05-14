from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from ..models import Chunk


def _tok(s: str) -> List[str]:
    # simple tokenizer: lowercase words + numbers
    return re.findall(r"[a-zA-Z0-9]+", (s or "").lower())


@dataclass
class SimpleReranker:
    """BM25-ish scoring + small structural boosts.

    - If query is None/empty: score by information density (length-based) and early-position bias.
    - If query provided: BM25-ish on tokens + early-position bias.
    """

    k1: float = 1.2
    b: float = 0.75
    early_pos_boost: float = 0.12

    def rank(self, chunks: List[Chunk], *, query: Optional[str] = None) -> List[Chunk]:
        if not chunks:
            return chunks

        if not query or not query.strip():
            for ch in chunks:
                # info density heuristic: log length, but penalize extremely long blocks
                L = max(1, len(ch.text))
                density = math.log(1.0 + L)
                penalty = 0.0 if L < 1800 else math.log(L / 1800.0)
                pos = 1.0 - (ch.order / max(1, len(chunks) - 1))
                ch.score = density - penalty + self.early_pos_boost * pos
                ch.features = {"len": L, "pos": pos}
            return sorted(chunks, key=lambda c: c.score, reverse=True)

        q = _tok(query)
        if not q:
            return self.rank(chunks, query=None)

        docs = [_tok(ch.text) for ch in chunks]
        N = len(docs)
        df = {}
        for tokens in docs:
            seen = set(tokens)
            for t in seen:
                df[t] = df.get(t, 0) + 1

        # idf with BM25 smoothing
        idf = {t: math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in set(q)}
        avgdl = sum(len(d) for d in docs) / max(1, N)

        for ch, tokens in zip(chunks, docs):
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            score = 0.0
            dl = len(tokens)
            for t in q:
                if t not in idf:
                    continue
                f = tf.get(t, 0)
                if f <= 0:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * (dl / (avgdl or 1.0)))
                score += idf[t] * (f * (self.k1 + 1)) / (denom or 1.0)

            pos = 1.0 - (ch.order / max(1, len(chunks) - 1))
            score += self.early_pos_boost * pos

            ch.score = score
            ch.features = {"dl": dl, "pos": pos, "query_terms": q}

        return sorted(chunks, key=lambda c: c.score, reverse=True)
