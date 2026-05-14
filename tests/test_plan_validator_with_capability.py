from __future__ import annotations

from sdk_test_agent.capability import BuildCapabilitySnapshotInput, CapabilityPanel, build_builtin_capability_registry
from sdk_test_agent.plan.plan_enums import SUPPORTED_PLAN_STEP_KINDS, PlanStatus, StepFailurePolicy, StepRiskLevel, ValidationStatus
from sdk_test_agent.plan.plan_models import ExecutionPlan, PlanStep
from sdk_test_agent.plan.plan_validation import PlanValidator


def _plan(inputs: dict) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan_1",
        task_id="task_1",
        task_type="sdk_deploy",
        goal="validate capability schema",
        planner_kind="demo",
        planner_name="test",
        planner_version="v1",
        status=PlanStatus.VALIDATED,
        steps=[
            PlanStep(
                step_id="run_date",
                title="Run date",
                kind="run_command",
                intent="inspect date",
                inputs=inputs,
                risk_level=StepRiskLevel.LOW,
                on_failure=StepFailurePolicy.ABORT,
            )
        ],
    )


def _snapshot():
    registry = build_builtin_capability_registry()
    return CapabilityPanel(registry).build_snapshot(BuildCapabilitySnapshotInput(available_context_keys=("command_controller",)))


def test_plan_validator_rejects_bad_run_command_inputs_with_capability_snapshot() -> None:
    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(_plan({"command": "date"}), capability_snapshot=_snapshot())

    assert result.status == ValidationStatus.FAILED
    assert "step.inputs.schema_invalid" in {issue.code for issue in result.issues}


def test_plan_validator_accepts_good_run_command_inputs_with_capability_snapshot() -> None:
    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(
        _plan({"action": "inspect_exec", "payload": {"cmd": ["date"]}}),
        capability_snapshot=_snapshot(),
    )

    assert result.passed is True


def test_plan_validator_can_use_registry_without_snapshot() -> None:
    registry = build_builtin_capability_registry()
    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS, capability_registry=registry).validate(_plan({"command": "date"}))

    assert result.status == ValidationStatus.FAILED
    assert "step.inputs.schema_invalid" in {issue.code for issue in result.issues}
