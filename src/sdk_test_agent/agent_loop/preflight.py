from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PreflightResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run_preflight(*, plan: dict[str, Any], execution_registry, runtime_bindings, capability_snapshot: dict[str, Any] | None = None) -> PreflightResult:
    errors: list[str] = []
    warnings: list[str] = []

    supported = set(execution_registry.supported_step_kinds())
    steps = list(plan.get("steps", []))
    for step in steps:
        kind = step.get("kind")
        if kind not in supported:
            errors.append(f"unknown step executor for step kind: {kind}")
        if kind == "run_command":
            action = (step.get("inputs") or {}).get("action")
            if action is not None:
                operators = getattr(getattr(runtime_bindings.command_controller, "dispatcher", None), "operators", {})
                if action not in operators:
                    errors.append(f"unknown action: {action}")

    return PreflightResult(passed=not errors, errors=errors, warnings=warnings)
