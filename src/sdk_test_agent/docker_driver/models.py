from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DriverConfig:
    base_url: str | None = None
    timeout: int = 60
    version: str | None = None
    use_ssh_client: bool = False


@dataclass(slots=True)
class ContainerCreateSpec:
    image: str
    command: list[str] | str
    working_dir: str = "/workspace"
    environment: dict[str, str] = field(default_factory=dict)
    detach: bool = True
    mem_limit: str | int | None = None
    nano_cpus: int | None = None
    network_disabled: bool = False
    read_only: bool = False
    user: str | None = None
    auto_remove: bool = False
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ContainerRef:
    container_id: str
    name: str | None = None
    status: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecCreateSpec:
    container_id: str
    argv: list[str]
    workdir: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    user: str | None = None
    tty: bool = False
    stream: bool = False
    demux: bool = True
