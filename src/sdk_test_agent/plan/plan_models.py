from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanStep:
    step_id: str
    title: str
    kind: str
    intent: str
    depends_on: list[str] = field(default_factory=list)
    branch_group: str | None = None
    branch_condition: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_outputs: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    timeout_sec: int | None = None
    retryable: bool = False
    optional: bool = False
    risk_level: str = "low"
    on_failure: str = "abort"
    on_success: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionPlan:
    plan_id: str
    task_id: str
    task_type: str
    goal: str
    planner_kind: str
    planner_name: str
    planner_version: str
    status: str
    steps: list[PlanStep]
    assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    global_constraints: dict[str, Any] = field(default_factory=dict)
    plan_metadata: dict[str, Any] = field(default_factory=dict)
    parent_plan_id: str | None = None
    revision_no: int = 0
    created_at: int | None = None


@dataclass(slots=True)
class ExecutionPlanDraft:
    task_id: str
    task_type: str
    goal: str
    planner_name: str
    planner_version: str
    plan_summary: str
    steps: list[PlanStep]
    assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    raw_llm_output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlanningPrerequisite:
    requirement_type: str
    required: bool
    reason: str
    satisfied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReplanRequest:
    task_id: str
    parent_plan_id: str
    reason: str
    failed_step_id: str | None = None
    execution_observations: list[str] = field(default_factory=list)
    latest_env_report_ref: str | None = None
    latest_artifact_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: int | None = None


@dataclass(slots=True)
class PlanRevision:
    parent_plan_id: str
    revision_no: int
    change_summary: str
    new_plan: ExecutionPlan
    replan_request: ReplanRequest | None = None
    created_at: int | None = None
