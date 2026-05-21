from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RuntimeBindings:
    artifact_manager: Any | None = None
    runtime_manager: Any | None = None
    docker_driver: Any | None = None
    command_controller: Any | None = None
    package_inspector: Any | None = None
    env_inspector: Any | None = None


@dataclass(slots=True)
class SdkRuntimeContext:
    bindings: RuntimeBindings
    capability_panel: Any
    planner: Any
    plan_finalizer: Any
    plan_validator: Any
    execution_engine: Any
    execution_registry: Any
    task_checker: Any
    loop_policy: Any
    clock: Any | None = None
    id_factory: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
