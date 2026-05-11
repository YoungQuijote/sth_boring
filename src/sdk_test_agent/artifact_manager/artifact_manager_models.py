from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    task_type: str
    status: str
    input_summary: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class TaskStageRecord:
    stage_id: str
    task_id: str
    stage_name: str
    status: str
    started_at: str | None
    ended_at: str | None
    metadata_json: str | None


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    task_id: str | None
    stage_id: str | None
    kind: str
    name: str | None
    storage_path: str
    content_hash: str | None
    mime_type: str | None
    size_bytes: int | None
    parent_artifact_id: str | None
    created_by_action: str | None
    created_at: str
    metadata_json: str | None
