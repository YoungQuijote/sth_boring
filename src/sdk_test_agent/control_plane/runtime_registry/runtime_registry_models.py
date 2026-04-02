from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HostRecord:
    host_id: str
    name: str | None
    address: str | None
    labels_json: str | None
    status: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class DockerEngineRecord:
    engine_id: str
    host_id: str
    name: str | None
    base_url: str
    connection_mode: str
    is_enabled: int
    last_seen_at: str | None
    health_status: str | None
    metadata_json: str | None


@dataclass(slots=True)
class ImageRecord:
    image_id: str
    engine_id: str
    repo_tags_json: str | None
    source_type: str
    source_ref: str | None
    created_at: str | None
    metadata_json: str | None


@dataclass(slots=True)
class ContainerRecord:
    container_id: str
    engine_id: str
    image_id: str | None
    name: str | None
    status: str | None
    workdir: str | None
    env_json: str | None
    ports_json: str | None
    labels_json: str | None
    created_at: str | None
    updated_at: str | None
    owner_task_id: str | None
    metadata_json: str | None


@dataclass(slots=True)
class DeploymentRecord:
    deployment_id: str
    task_id: str | None
    sdk_name: str
    sdk_version: str | None
    engine_id: str | None
    image_id: str | None
    container_id: str | None
    env_fingerprint: str | None
    status: str | None
    reusable: int
    created_at: str | None
    updated_at: str | None
    metadata_json: str | None
