from __future__ import annotations

from typing import Any, Literal

from ._pydantic_compat import BaseModel, ConfigDict, Field


class CapabilityResolutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    input_payload: dict[str, Any]
    output_snapshot_id: str
    output_capability_digest: str
    descriptor_ids: list[str]
    enabled_capability_ids: list[str]
    disabled_capability_ids: list[str]
    unavailable_capability_ids: list[str]
    placeholder_capability_ids: list[str]
    deprecated_capability_ids: list[str]
    availability_records: list[dict[str, Any]]
    created_at: float
    task_id: str | None = None
    action_name: Literal["capability.build_snapshot"] = "capability.build_snapshot"
    prompt_artifact_id: str | None = None
    snapshot_artifact_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
