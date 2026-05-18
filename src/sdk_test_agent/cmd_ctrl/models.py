from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GuardDecisionType = Literal["allow", "deny", "escalate"]
from typing import Any


@dataclass(slots=True)
class ActionRequest:
    action: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ActionResponse:
    ok: bool
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class GuardDecision:
    decision: GuardDecisionType
    reason: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
