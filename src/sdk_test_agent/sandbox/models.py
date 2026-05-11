from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SandboxStatus = Literal[
    "created",
    "image_ready",
    "container_running",
    "workspace_ready",
    "ready",
    "stopped",
    "removed",
    "failed",
]


@dataclass(slots=True)
class SandboxSpec:
    sandbox_id: str
    language: str = "python"
    image: str = "python:3.11-slim"
    workdir: str = "/workspace"
    env: dict[str, str] = field(default_factory=dict)
    mem_limit: str | int | None = "1g"
    nano_cpus: int | None = None
    network_disabled: bool = False
    read_only_rootfs: bool = False
    user: str | None = None
    auto_remove: bool = False
    pull_policy: Literal["always", "if_missing", "never"] = "if_missing"
    keep_alive_cmd: list[str] = field(default_factory=lambda: ["sleep", "infinity"])
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExecSpec:
    argv: list[str]
    workdir: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    user: str | None = None
    tty: bool = False
    stream: bool = False
    demux: bool = True


@dataclass(slots=True)
class ExecResult:
    exit_code: int | None
    stdout: bytes | None = None
    stderr: bytes | None = None
    combined: bytes | None = None
    duration_sec: float = 0.0
    timed_out: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SandboxSnapshot:
    sandbox_id: str
    status: SandboxStatus
    image: str
    container_id: str | None
    workdir: str
    attrs: dict[str, Any] = field(default_factory=dict)
