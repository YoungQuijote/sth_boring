from __future__ import annotations

TABLE_TASKS = "tasks"
TABLE_TASK_STAGES = "task_stages"
TABLE_ARTIFACTS = "artifacts"
TABLE_ACTION_RUNS = "action_runs"
TABLE_ARTIFACT_LINKS = "artifact_links"

SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        status TEXT NOT NULL,
        input_summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS task_stages (
        stage_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        stage_name TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        ended_at TEXT,
        metadata_json TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(task_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id TEXT PRIMARY KEY,
        task_id TEXT,
        stage_id TEXT,
        kind TEXT NOT NULL,
        name TEXT,
        storage_path TEXT NOT NULL,
        content_hash TEXT,
        mime_type TEXT,
        size_bytes INTEGER,
        parent_artifact_id TEXT,
        created_by_action TEXT,
        created_at TEXT NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(task_id),
        FOREIGN KEY(stage_id) REFERENCES task_stages(stage_id),
        FOREIGN KEY(parent_artifact_id) REFERENCES artifacts(artifact_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS action_runs (
        action_run_id TEXT PRIMARY KEY,
        task_id TEXT,
        stage_id TEXT,
        action_name TEXT NOT NULL,
        status TEXT NOT NULL,
        request_json TEXT,
        response_json TEXT,
        started_at TEXT,
        ended_at TEXT,
        error_text TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(task_id),
        FOREIGN KEY(stage_id) REFERENCES task_stages(stage_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS artifact_links (
        link_id TEXT PRIMARY KEY,
        src_artifact_id TEXT NOT NULL,
        dst_artifact_id TEXT NOT NULL,
        relation TEXT NOT NULL,
        FOREIGN KEY(src_artifact_id) REFERENCES artifacts(artifact_id),
        FOREIGN KEY(dst_artifact_id) REFERENCES artifacts(artifact_id)
    );
    """,
]
