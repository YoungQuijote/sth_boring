from __future__ import annotations

from dataclasses import dataclass, field

from agent_crawler.models import QualityScore
from webkit.models import Document


@dataclass(frozen=True)
class QualityThresholds:
    min_text_chars: int = 200
    min_chunks: int = 1
    max_link_density: float = 0.8


@dataclass
class QualityAssessor:
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)

    def score(self, doc: Document) -> QualityScore:
        text = doc.text or ""
        text_chars = len(text.strip())
        chunk_count = len(doc.chunks)
        link_count = len(doc.links)
        wordish_count = max(1, len(text.split()))
        link_density = link_count / wordish_count
        unique_line_ratio = self._unique_line_ratio(text)

        score = 1.0
        reasons: list[str] = []
        if text_chars < self.thresholds.min_text_chars:
            score -= 0.45
            reasons.append("text_too_short")
        if chunk_count < self.thresholds.min_chunks:
            score -= 0.25
            reasons.append("no_chunks")
        if link_density > self.thresholds.max_link_density:
            score -= 0.2
            reasons.append("link_density_high")
        if unique_line_ratio < 0.35 and text_chars > 0:
            score -= 0.1
            reasons.append("repeated_lines")

        score = max(0.0, min(1.0, score))
        return QualityScore(
            score=score,
            ok=not reasons,
            reasons=reasons,
            metrics={
                "text_chars": text_chars,
                "chunk_count": chunk_count,
                "link_count": link_count,
                "link_density": link_density,
                "unique_line_ratio": unique_line_ratio,
            },
        )

    def _unique_line_ratio(self, text: str) -> float:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return 0.0
        return len(set(lines)) / len(lines)
