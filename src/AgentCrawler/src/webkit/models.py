from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass(frozen=True)
class CandidateURL:
    url: str
    score: float = 0.0
    source: str = "seed"
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FetchResponse:
    url: str
    final_url: str
    status_code: int
    headers: Dict[str, str]
    content: bytes
    encoding: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def text(self) -> str:
        enc = self.encoding or "utf-8"
        return self.content.decode(enc, errors="replace")

@dataclass
class Chunk:
    text: str
    order: int
    source_url: str
    title: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    features: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Document:
    url: str
    title: Optional[str]
    text: str
    links: List[str] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
