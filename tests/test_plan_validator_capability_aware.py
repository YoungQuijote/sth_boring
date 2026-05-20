from __future__ import annotations

from sdk_test_agent.capability import BuildCapabilitySnapshotInput, CapabilityPanel, build_builtin_capability_registry
from sdk_test_agent.plan import PlanFinalizer
from sdk_test_agent.plan.plan_enums import SUPPORTED_PLAN_STEP_KINDS, PlanStatus, StepFailurePolicy, StepRiskLevel, ValidationStatus
from sdk_test_agent.plan.plan_models import ExecutionPlan, ExecutionPlanDraft, PlanStep
from sdk_test_agent.plan.plan_validation import PlanValidator


def _snapshot():
    return CapabilityPanel(build_builtin_capability_registry()).build_snapshot(
        BuildCapabilitySnapshotInput(available_context_keys=("command_controller",), max_risk_level="medium")
    )


def _plan_for_step(step: PlanStep, *, capability_digest: str | None = None) -> ExecutionPlan:
    plan = ExecutionPlan(
        plan_id="plan_1",
        task_id="task_1",
        task_type="sdk_deploy",
        goal="validate capability-aware plan",
        planner_kind="llm",
        planner_name="test",
        planner_version="v1",
        status=PlanStatus.DRAFT,
        steps=[step],
        plan_metadata={},
    )
    if capability_digest is not None:
        plan.plan_metadata["capability_digest"] = capability_digest
    return plan


def _run_command_step(*, inputs: dict | None = None, required_capabilities: list[str] | None = None) -> PlanStep:
    return PlanStep(
        step_id="step_run_command",
        title="Run command",
        kind="run_command",
        intent="inspect command output",
        inputs=inputs if inputs is not None else {"action": "inspect_exec", "payload": {"cmd": ["date"]}},
        required_capabilities=required_capabilities if required_capabilities is not None else ["cap.run_command.inspect_exec.v1"],
        risk_level=StepRiskLevel.LOW,
        on_failure=StepFailurePolicy.ABORT,
    )


def test_capability_aware_validator_keeps_legacy_mode_compatible_without_snapshot() -> None:
    plan = _plan_for_step(_run_command_step(inputs={"command": "date"}, required_capabilities=[]))

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan)

    assert result.passed is True


def test_capability_aware_validator_rejects_placeholder_step_kind() -> None:
    snapshot = _snapshot()
    step = PlanStep(step_id="step_script", title="Generate", kind="generate_script", intent="generate script")

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(_plan_for_step(step, capability_digest=snapshot.capability_digest), capability_snapshot=snapshot)

    assert result.status == ValidationStatus.FAILED
    assert "CAPABILITY_PLACEHOLDER_USED" in {issue.code for issue in result.errors}


def test_capability_aware_validator_rejects_input_schema_errors() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step(inputs={"command": "date"}), capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.status == ValidationStatus.FAILED
    assert "STEP_INPUT_SCHEMA_INVALID" in {issue.code for issue in result.errors}


def test_capability_aware_validator_warns_for_missing_required_capabilities_by_default() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step(required_capabilities=[]), capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.passed is True
    assert "CAPABILITY_REQUIRED_MISSING" in {issue.code for issue in result.warnings}


def test_capability_aware_validator_rejects_missing_required_capabilities_in_strict_mode() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step(required_capabilities=[]), capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS, strict_required_capabilities=True).validate(plan, capability_snapshot=snapshot)

    assert result.status == ValidationStatus.FAILED
    assert "CAPABILITY_REQUIRED_MISSING" in {issue.code for issue in result.errors}


def test_capability_aware_validator_rejects_unknown_required_capability() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step(required_capabilities=["inspection.package.java"]), capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.status == ValidationStatus.FAILED
    assert "CAPABILITY_REQUIRED_UNKNOWN" in {issue.code for issue in result.errors}


def test_capability_aware_validator_rejects_digest_mismatch() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step(), capability_digest="sha256:not-the-snapshot")

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.status == ValidationStatus.FAILED
    assert "CAPABILITY_DIGEST_MISMATCH" in {issue.code for issue in result.errors}


def test_capability_aware_validator_warns_for_missing_digest_unless_required() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step())

    default_result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)
    strict_result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS, require_capability_digest=True).validate(plan, capability_snapshot=snapshot)

    assert default_result.passed is True
    assert "CAPABILITY_DIGEST_MISSING" in {issue.code for issue in default_result.warnings}
    assert strict_result.status == ValidationStatus.FAILED
    assert "CAPABILITY_DIGEST_MISSING" in {issue.code for issue in strict_result.errors}


def test_capability_aware_validator_accepts_valid_run_command() -> None:
    snapshot = _snapshot()
    plan = _plan_for_step(_run_command_step(), capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.passed is True
    assert result.errors == []
    assert result.metadata["capability_digest"] == snapshot.capability_digest


def test_capability_aware_validator_accepts_run_python_shape_declared_by_capability_schema() -> None:
    snapshot = _snapshot()
    step = _run_command_step(
        inputs={"action": "run_python", "payload": {"argv": ["-c", "print(\'hello\')"], "timeout_sec": 30}},
        required_capabilities=["cap.run_command.inspect_exec.v1"],
    )
    plan = _plan_for_step(step, capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.passed is True


def test_capability_aware_validator_does_not_modify_plan_status_or_step_payload() -> None:
    snapshot = _snapshot()
    step = _run_command_step()
    plan = _plan_for_step(step, capability_digest=snapshot.capability_digest)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert result.passed is True
    assert plan.status == PlanStatus.DRAFT
    assert step.inputs == {"action": "inspect_exec", "payload": {"cmd": ["date"]}}


def test_plan_finalizer_and_capability_aware_validator_happy_path() -> None:
    snapshot = _snapshot()
    draft = ExecutionPlanDraft(
        task_id="task_1",
        task_type="sdk_deploy",
        goal="validate finalized plan",
        planner_name="llm_planner",
        planner_version="v1",
        plan_summary="run command",
        steps=[_run_command_step()],
    )

    plan = PlanFinalizer(clock=lambda: 123).finalize(draft, capability_snapshot=snapshot)
    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS).validate(plan, capability_snapshot=snapshot)

    assert plan.plan_metadata["capability_digest"] == snapshot.capability_digest
    assert result.passed is True
