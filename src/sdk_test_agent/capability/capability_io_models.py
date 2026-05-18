from __future__ import annotations

from typing import Any, Literal

from ._pydantic_compat import BaseModel, ConfigDict, Field


class InspectExecPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cmd: list[str] = Field(min_length=1)
    cwd: str | None = None
    timeout_sec: int = Field(default=30, ge=1, le=300)


class RunCommandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["inspect_exec"]
    payload: InspectExecPayload


class RunCommandOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifact_refs: list[str] = Field(default_factory=list)


class InspectPackageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_type: Literal["java", "python", "unknown"] = "unknown"
    input_refs: dict[str, str] = Field(default_factory=dict)


class InspectPackageOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    inspection_status: str
    package_report: dict[str, Any] = Field(default_factory=dict)


class DockerfileRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_ref: str
    path_in_context: str | None = None


class BuildContextRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_ref: str | None = None
    context_dir: str | None = None


class BuildImageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_name: str
    dockerfile: DockerfileRef
    tag: str | None = None
    context: BuildContextRef | None = None
    build_args: dict[str, str] = Field(default_factory=dict)


class BuildImageOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    image_ref: str | None = None
    image_id: str | None = None
    build_log_artifact_id: str | None = None


class CreateRuntimeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_ref: str
    name: str | None = None
    command: list[str] | None = None
    env: dict[str, str] = Field(default_factory=dict)
    ports: dict[str, str] = Field(default_factory=dict)
    start: bool = True
    reusable: bool = False


class CreateRuntimeOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    runtime_ref: str | None = None
    container_id: str | None = None
    deployment_id: str | None = None


class InspectEnvironmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime_ref: str | None = None
    container_id: str | None = None
    probes: list[str] = Field(default_factory=list)


class InspectEnvironmentOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    env_status: str
    env_report: dict[str, Any] = Field(default_factory=dict)


class ExecuteProbeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probe_name: str
    payload: InspectExecPayload
    action: Literal["inspect_exec"] = "inspect_exec"


class ExecuteProbeOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    probe_status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    artifact_refs: list[str] = Field(default_factory=list)


class CollectArtifactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_path: str
    artifact_kind: str
    mime_type: str = "application/octet-stream"
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectArtifactOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    artifact_id: str | None = None
    artifact_ref: str | None = None


class EmptyPlaceholderInput(BaseModel):
    model_config = ConfigDict(extra="allow")


class EmptyPlaceholderOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
