from __future__ import annotations

from typing import Any

from ._pydantic_compat import BaseModel, ConfigDict, Field
from .capability_enums import CapabilityRiskLevel, CapabilityStatus, CapabilityVisibility


class CapabilityDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    capability_id: str
    version: str
    step_kind: str
    owner_module: str
    name: str
    description: str
    executor_name: str | None = None
    input_model_ref: str | None = None
    output_model_ref: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_context_keys: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.LOW
    visibility: CapabilityVisibility = CapabilityVisibility.PLANNER_VISIBLE
    default_enabled: bool = True
    is_placeholder: bool = False
    is_deprecated: bool = False
    examples: tuple[dict[str, Any], ...] = ()
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class BuildCapabilitySnapshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str | None = None
    task_type: str | None = None
    available_context_keys: tuple[str, ...] = ()
    required_capability_ids: tuple[str, ...] = ()
    recommended_capability_ids: tuple[str, ...] = ()
    forbidden_capability_ids: tuple[str, ...] = ()
    max_risk_level: CapabilityRiskLevel = CapabilityRiskLevel.MEDIUM
    allow_placeholder: bool = False
    allow_deprecated: bool = False
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityAvailability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    capability_id: str
    step_kind: str
    status: CapabilityStatus
    reason: str | None = None
    missing_context_keys: tuple[str, ...] = ()
    blocked_by_policy: bool = False
    blocked_by_skill: bool = False
    blocked_by_feature_flag: bool = False
    effective_risk_level: CapabilityRiskLevel = CapabilityRiskLevel.LOW


class CapabilitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: str
    capabilities: tuple[CapabilityDescriptor, ...]
    availability: tuple[CapabilityAvailability, ...]
    available_step_kinds: tuple[str, ...]
    unavailable_step_kinds: tuple[str, ...]
    capability_digest: str
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
