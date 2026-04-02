from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class JavaDeployInput:
    sdk_name: str
    sdk_version: str | None
    jar_bytes: bytes
    pom_xml_bytes: bytes
    settings_xml_bytes: bytes | None = None
    jdk_bytes: bytes | None = None


@dataclass(slots=True)
class MinimalLoopResult:
    task_id: str
    image_id: str
    container_id: str
    deployment_id: str
    artifact_ids: list[str]
    package_inspection_status: str | None = None
    env_inspection_status: str | None = None
