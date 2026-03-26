from __future__ import annotations

import sqlite3

from .runtime_registry_models import ContainerRecord, DeploymentRecord, DockerEngineRecord, HostRecord, ImageRecord
from .runtime_registry_schema import SCHEMA_SQL


class RuntimeRegistryRepo:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            for sql in SCHEMA_SQL:
                conn.execute(sql)
            conn.commit()

    def insert_host(self, rec: HostRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO hosts(host_id,name,address,labels_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (rec.host_id, rec.name, rec.address, rec.labels_json, rec.status, rec.created_at, rec.updated_at),
            )
            conn.commit()

    def insert_engine(self, rec: DockerEngineRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO docker_engines(engine_id,host_id,name,base_url,connection_mode,is_enabled,last_seen_at,health_status,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    rec.engine_id,
                    rec.host_id,
                    rec.name,
                    rec.base_url,
                    rec.connection_mode,
                    rec.is_enabled,
                    rec.last_seen_at,
                    rec.health_status,
                    rec.metadata_json,
                ),
            )
            conn.commit()

    def insert_image(self, rec: ImageRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO images(image_id,engine_id,repo_tags_json,source_type,source_ref,created_at,metadata_json) VALUES(?,?,?,?,?,?,?)",
                (rec.image_id, rec.engine_id, rec.repo_tags_json, rec.source_type, rec.source_ref, rec.created_at, rec.metadata_json),
            )
            conn.commit()

    def insert_container(self, rec: ContainerRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO containers(container_id,engine_id,image_id,name,status,workdir,env_json,ports_json,labels_json,created_at,updated_at,owner_task_id,metadata_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec.container_id,
                    rec.engine_id,
                    rec.image_id,
                    rec.name,
                    rec.status,
                    rec.workdir,
                    rec.env_json,
                    rec.ports_json,
                    rec.labels_json,
                    rec.created_at,
                    rec.updated_at,
                    rec.owner_task_id,
                    rec.metadata_json,
                ),
            )
            conn.commit()

    def upsert_container_status(self, container_id: str, status: str, updated_at: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE containers SET status=?, updated_at=? WHERE container_id=?", (status, updated_at, container_id))
            conn.commit()

    def insert_deployment(self, rec: DeploymentRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO deployments(deployment_id,task_id,sdk_name,sdk_version,engine_id,image_id,container_id,env_fingerprint,status,reusable,created_at,updated_at,metadata_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec.deployment_id,
                    rec.task_id,
                    rec.sdk_name,
                    rec.sdk_version,
                    rec.engine_id,
                    rec.image_id,
                    rec.container_id,
                    rec.env_fingerprint,
                    rec.status,
                    rec.reusable,
                    rec.created_at,
                    rec.updated_at,
                    rec.metadata_json,
                ),
            )
            conn.commit()
