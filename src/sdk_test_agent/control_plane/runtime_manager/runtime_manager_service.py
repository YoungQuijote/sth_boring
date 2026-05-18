from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.docker_driver_models import ContainerCreateSpec

from ..runtime_registry.runtime_registry_enums import ImageSourceType
from ..runtime_registry.runtime_registry_models import ContainerRecord, DeploymentRecord, DockerEngineRecord, HostRecord, ImageRecord
from ..runtime_registry.runtime_registry_repo import RuntimeRegistryRepo
from .runtime_manager_models import EnvFingerprintInput


class RuntimeManagerService:
    def __init__(self, driver: BaseDockerDriver, registry_repo: RuntimeRegistryRepo, engine_id: str, now_fn) -> None:
        self.driver = driver
        self.registry_repo = registry_repo
        self.engine_id = engine_id
        self.now_fn = now_fn

    def register_host(self, host_id: str, name: str | None, address: str | None, labels_json: str, status: str = "active") -> HostRecord:
        rec = HostRecord(
            host_id=host_id,
            name=name,
            address=address,
            labels_json=labels_json,
            status=status,
            created_at=self.now_fn(),
            updated_at=self.now_fn(),
        )
        self.registry_repo.insert_host(rec)
        return rec

    def register_engine(self, host_id: str, base_url: str, connection_mode: str, name: str | None = None) -> DockerEngineRecord:
        rec = DockerEngineRecord(
            engine_id=self.engine_id,
            host_id=host_id,
            name=name,
            base_url=base_url,
            connection_mode=connection_mode,
            is_enabled=1,
            last_seen_at=self.now_fn(),
            health_status="unknown",
            metadata_json=None,
        )
        self.registry_repo.insert_engine(rec)
        return rec

    def register_image(self, image_id: str, tags: list[str], source_type: str, source_ref: str | None) -> ImageRecord:
        rec = ImageRecord(
            image_id=image_id,
            engine_id=self.engine_id,
            repo_tags_json=json.dumps(tags, sort_keys=True),
            source_type=source_type,
            source_ref=source_ref,
            created_at=self.now_fn(),
            metadata_json=None,
        )
        self.registry_repo.insert_image(rec)
        return rec

    def create_container(self, spec: ContainerCreateSpec, owner_task_id: str | None = None) -> ContainerRecord:
        ref = self.driver.create_container(spec)
        self.driver.start_container(ref.container_id)
        rec = ContainerRecord(
            container_id=ref.container_id,
            engine_id=self.engine_id,
            image_id=spec.image,
            name=ref.name,
            status="running",
            workdir=spec.working_dir,
            env_json=json.dumps(spec.environment, sort_keys=True),
            ports_json=json.dumps([], sort_keys=True),
            labels_json=json.dumps(spec.labels, sort_keys=True),
            created_at=self.now_fn(),
            updated_at=self.now_fn(),
            owner_task_id=owner_task_id,
            metadata_json=json.dumps({"command": spec.command}),
        )
        self.registry_repo.insert_container(rec)
        return rec

    def remove_container(self, container_id: str) -> None:
        self.driver.remove_container(container_id, force=True, remove_volumes=False)
        self.registry_repo.upsert_container_status(container_id, "removed", self.now_fn())

    @staticmethod
    def make_env_fingerprint(payload: EnvFingerprintInput) -> tuple[str, str]:
        raw = json.dumps(asdict(payload), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), raw

    def create_deployment_record(
        self,
        *,
        task_id: str,
        sdk_name: str,
        sdk_version: str | None,
        image_id: str,
        container_id: str,
        fingerprint_payload: EnvFingerprintInput,
        reusable: int,
    ) -> DeploymentRecord:
        fp, raw = self.make_env_fingerprint(fingerprint_payload)
        rec = DeploymentRecord(
            deployment_id=f"deploy_{hashlib.sha1((task_id+container_id).encode()).hexdigest()[:26].upper()}",
            task_id=task_id,
            sdk_name=sdk_name,
            sdk_version=sdk_version,
            engine_id=self.engine_id,
            image_id=image_id,
            container_id=container_id,
            env_fingerprint=fp,
            status="ready",
            reusable=reusable,
            created_at=self.now_fn(),
            updated_at=self.now_fn(),
            metadata_json=raw,
        )
        self.registry_repo.insert_deployment(rec)
        return rec
