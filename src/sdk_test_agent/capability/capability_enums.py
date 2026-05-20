from __future__ import annotations

from enum import Enum


class CapabilityStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    PLACEHOLDER = "placeholder"
    DEPRECATED = "deprecated"


class CapabilityRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CapabilityVisibility(str, Enum):
    PLANNER_VISIBLE = "planner_visible"
    VALIDATOR_ONLY = "validator_only"
    INTERNAL = "internal"


RISK_ORDER: dict[str, int] = {
    CapabilityRiskLevel.LOW: 0,
    CapabilityRiskLevel.MEDIUM: 1,
    CapabilityRiskLevel.HIGH: 2,
    CapabilityRiskLevel.CRITICAL: 3,
}
