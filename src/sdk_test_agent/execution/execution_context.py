from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionContext:
    task_id: str
    plan_id: str
    run_id: str
    artifact_manager: Any | None = None
    runtime_manager: Any | None = None
    docker_driver: Any | None = None
    command_controller: Any | None = None
    package_inspector: Any | None = None
    env_inspector: Any | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    artifact_refs: dict[str, str] = field(default_factory=dict)
    runtime_refs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
