from __future__ import annotations

TABLE_HOSTS = "hosts"
TABLE_DOCKER_ENGINES = "docker_engines"
TABLE_IMAGES = "images"
TABLE_CONTAINERS = "containers"
TABLE_DEPLOYMENTS = "deployments"
TABLE_CONTAINER_RELATIONS = "container_relations"

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS hosts (
        host_id TEXT PRIMARY KEY,
        name TEXT UNIQUE,
        address TEXT,
        labels_json TEXT,
        status TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS docker_engines (
        engine_id TEXT PRIMARY KEY,
        host_id TEXT NOT NULL,
        name TEXT,
        base_url TEXT NOT NULL,
        connection_mode TEXT NOT NULL,
        is_enabled INTEGER NOT NULL,
        last_seen_at TEXT,
        health_status TEXT,
        metadata_json TEXT,
        FOREIGN KEY(host_id) REFERENCES hosts(host_id)
    );""",
    """CREATE TABLE IF NOT EXISTS images (
        image_id TEXT PRIMARY KEY,
        engine_id TEXT NOT NULL,
        repo_tags_json TEXT,
        source_type TEXT NOT NULL,
        source_ref TEXT,
        created_at TEXT,
        metadata_json TEXT,
        FOREIGN KEY(engine_id) REFERENCES docker_engines(engine_id)
    );""",
    """CREATE TABLE IF NOT EXISTS containers (
        container_id TEXT PRIMARY KEY,
        engine_id TEXT NOT NULL,
        image_id TEXT,
        name TEXT,
        status TEXT,
        workdir TEXT,
        env_json TEXT,
        ports_json TEXT,
        labels_json TEXT,
        created_at TEXT,
        updated_at TEXT,
        owner_task_id TEXT,
        metadata_json TEXT,
        FOREIGN KEY(engine_id) REFERENCES docker_engines(engine_id),
        FOREIGN KEY(image_id) REFERENCES images(image_id)
    );""",
    """CREATE TABLE IF NOT EXISTS deployments (
        deployment_id TEXT PRIMARY KEY,
        task_id TEXT,
        sdk_name TEXT NOT NULL,
        sdk_version TEXT,
        engine_id TEXT,
        image_id TEXT,
        container_id TEXT,
        env_fingerprint TEXT,
        status TEXT,
        reusable INTEGER NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        metadata_json TEXT,
        FOREIGN KEY(engine_id) REFERENCES docker_engines(engine_id),
        FOREIGN KEY(image_id) REFERENCES images(image_id),
        FOREIGN KEY(container_id) REFERENCES containers(container_id)
    );""",
    """CREATE TABLE IF NOT EXISTS container_relations (
        relation_id TEXT PRIMARY KEY,
        src_container_id TEXT NOT NULL,
        dst_container_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY(src_container_id) REFERENCES containers(container_id),
        FOREIGN KEY(dst_container_id) REFERENCES containers(container_id)
    );""",
]
