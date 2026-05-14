from __future__ import annotations

from dataclasses import dataclass, field

from ..inspection_models import InspectionReportBase


@dataclass(slots=True)
class DockerEnvInspectionInput:
    engine_id: str
    image_id: str | None
    container_id: str
    runtime_name: str = "docker"


@dataclass(slots=True)
class ProbeRecord:
    probe_name: str
    command: list[str]
    ok: bool
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None


@dataclass(slots=True)
class EnvInspectionReport(InspectionReportBase):
    runtime_type: str = "docker"
    engine_id: str | None = None
    image_id: str | None = None
    container_id: str | None = None
    container_status: str | None = None
    tool_versions: dict[str, str] = field(default_factory=dict)
    env_vars: dict[str, str] = field(default_factory=dict)
    workdir: str | None = None
    ports: list[str] = field(default_factory=list)
    process_summary: list[str] = field(default_factory=list)
    readiness: str = "unknown"
    probe_records: list[ProbeRecord] = field(default_factory=list)
