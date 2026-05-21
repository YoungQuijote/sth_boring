from __future__ import annotations

import sqlite3
from dataclasses import asdict

from .artifact_manager_models import ArtifactRecord, TaskRecord, TaskStageRecord
from .artifact_manager_schema import SCHEMA_SQL


class ArtifactManagerRepo:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            for sql in SCHEMA_SQL:
                conn.execute(sql)
            conn.commit()

    def insert_task(self, rec: TaskRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tasks(task_id, task_type, status, input_summary, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                (rec.task_id, rec.task_type, rec.status, rec.input_summary, rec.created_at, rec.updated_at),
            )
            conn.commit()

    def insert_stage(self, rec: TaskStageRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO task_stages(stage_id, task_id, stage_name, status, started_at, ended_at, metadata_json) VALUES(?,?,?,?,?,?,?)",
                (rec.stage_id, rec.task_id, rec.stage_name, rec.status, rec.started_at, rec.ended_at, rec.metadata_json),
            )
            conn.commit()

    def insert_artifact(self, rec: ArtifactRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO artifacts(
                    artifact_id, task_id, stage_id, kind, name, storage_path, content_hash, mime_type,
                    size_bytes, parent_artifact_id, created_by_action, created_at, metadata_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec.artifact_id,
                    rec.task_id,
                    rec.stage_id,
                    rec.kind,
                    rec.name,
                    rec.storage_path,
                    rec.content_hash,
                    rec.mime_type,
                    rec.size_bytes,
                    rec.parent_artifact_id,
                    rec.created_by_action,
                    rec.created_at,
                    rec.metadata_json,
                ),
            )
            conn.commit()
