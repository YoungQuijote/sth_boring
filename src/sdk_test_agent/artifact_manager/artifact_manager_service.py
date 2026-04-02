from __future__ import annotations

import os

from .artifact_manager_enums import TaskStatus
from .artifact_manager_models import ArtifactRecord, TaskRecord, TaskStageRecord
from .artifact_manager_repo import ArtifactManagerRepo
from .artifact_manager_utils import ensure_task_dirs, new_id, now_iso, sha256_bytes


class ArtifactManagerService:
    def __init__(self, repo: ArtifactManagerRepo, artifact_root_dir: str) -> None:
        self.repo = repo
        self.artifact_root_dir = artifact_root_dir

    def create_task(self, task_type: str, input_summary: str | None) -> TaskRecord:
        task_id = new_id("task")
        now = now_iso()
        rec = TaskRecord(task_id=task_id, task_type=task_type, status=TaskStatus.CREATED, input_summary=input_summary, created_at=now, updated_at=now)
        self.repo.insert_task(rec)
        ensure_task_dirs(self.artifact_root_dir, task_id)
        return rec

    def create_stage(self, task_id: str, stage_name: str, status: str, metadata_json: str | None = None) -> TaskStageRecord:
        rec = TaskStageRecord(
            stage_id=new_id("stage"),
            task_id=task_id,
            stage_name=stage_name,
            status=status,
            started_at=now_iso(),
            ended_at=None,
            metadata_json=metadata_json,
        )
        self.repo.insert_stage(rec)
        return rec

    def persist_artifact_bytes(
        self,
        *,
        task_id: str,
        stage_id: str | None,
        kind: str,
        name: str,
        content: bytes,
        subdir: str,
        mime_type: str | None = None,
        created_by_action: str | None = None,
    ) -> ArtifactRecord:
        dirs = ensure_task_dirs(self.artifact_root_dir, task_id)
        base = dirs.get(subdir, dirs["root"])
        path = os.path.join(base, name)
        with open(path, "wb") as f:
            f.write(content)

        rec = ArtifactRecord(
            artifact_id=new_id("artifact"),
            task_id=task_id,
            stage_id=stage_id,
            kind=kind,
            name=name,
            storage_path=path,
            content_hash=sha256_bytes(content),
            mime_type=mime_type,
            size_bytes=len(content),
            parent_artifact_id=None,
            created_by_action=created_by_action,
            created_at=now_iso(),
            metadata_json=None,
        )
        self.repo.insert_artifact(rec)
        return rec
