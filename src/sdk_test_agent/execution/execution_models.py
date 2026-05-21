from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionRun:
    run_id: str
    task_id: str
    plan_id: str
    status: str
    started_at: int | None = None
    finished_at: int | None = None
    step_runs: list["ExecutionStepRun"] = field(default_factory=list)
    result_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionStepRun:
    step_run_id: str
    run_id: str
    step_id: str
    step_kind: str
    status: str
    started_at: int | None = None
    finished_at: int | None = None
    duration_ms: int | None = None
    inputs_snapshot: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[str] = field(default_factory=list)
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    log_ref: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StepExecutionResult:
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[str] = field(default_factory=list)
    stdout: str | None = None
    stderr: str | None = None
    log_text: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionRunResult:
    run: ExecutionRun
    status: str
    step_results: dict[str, StepExecutionResult] = field(default_factory=dict)
    replan_request: Any | None = None
    artifact_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
