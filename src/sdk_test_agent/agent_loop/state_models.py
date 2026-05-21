from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class SdkAgentState(TypedDict, total=False):
    task_id: str
    task_type: str
    user_goal: str
    iteration: int
    max_iterations: int
    loop_status: str
    available_context_keys: list[str]
    capability_snapshot_id: str
    capability_digest: str
    capability_prompt: str
    capability_snapshot: dict[str, Any]
    selected_skill_ids: list[str]
    skill_context: str
    draft_plan: dict[str, Any]
    plan_id: str
    plan: dict[str, Any]
    validation_result: dict[str, Any]
    preflight_result: dict[str, Any]
    run_id: str
    execution_result: dict[str, Any]
    task_check_decision: dict[str, Any]
    replan_request: dict[str, Any]
    artifact_refs: list[str]
    stage_refs: list[str]
    errors: list[dict[str, Any]]
    metadata: dict[str, Any]
