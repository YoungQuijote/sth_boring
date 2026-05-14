from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuthProfile:
    profile_id: str = "anonymous"
    secrets_refs: dict[str, str] = field(default_factory=dict)
    storage_state_path: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
