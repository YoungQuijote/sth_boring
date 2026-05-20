from __future__ import annotations

from sdk_test_agent.plan import PlanFinalizer
from sdk_test_agent.plan.plan_enums import PlanStatus, PlannerKind
from sdk_test_agent.plan.plan_models import ExecutionPlanDraft, PlanStep


def _draft(step: PlanStep | None = None) -> ExecutionPlanDraft:
    return ExecutionPlanDraft(
        task_id="task_1",
        task_type="sdk_deploy",
        goal="Deploy and verify SDK",
        planner_name="llm_planner",
        planner_version="0.1.0",
        plan_summary="simple deploy plan",
        steps=[step or PlanStep(step_id="s1", title="Inspect", kind="inspect_package", intent="inspect input")],
        assumptions=["jar exists"],
        missing_information=["port unknown"],
        risk_notes=["low risk"],
        raw_llm_output='{"plan_summary":"simple deploy plan"}',
        metadata={"source": "unit-test"},
    )


def test_plan_finalizer_basic_finalize() -> None:
    draft = _draft()
    plan = PlanFinalizer(clock=lambda: 1234567890).finalize(draft)

    assert plan.plan_id.startswith("plan_")
    assert plan.status == PlanStatus.DRAFT
    assert plan.task_id == draft.task_id
    assert plan.task_type == draft.task_type
    assert plan.goal == draft.goal
    assert plan.planner_kind == PlannerKind.LLM
    assert plan.planner_name == draft.planner_name
    assert plan.planner_version == draft.planner_version
    assert plan.steps == draft.steps
    assert plan.created_at == 1234567890
    assert plan.plan_metadata["plan_summary"] == draft.plan_summary
    assert plan.plan_metadata["raw_llm_output"] == draft.raw_llm_output
    assert plan.plan_metadata["draft_metadata"] == draft.metadata


def test_plan_finalizer_injects_capability_metadata() -> None:
    class FakeSnapshot:
        snapshot_id = "capsnap_123"
        capability_digest = "sha256:abc"

    class FakeRecord:
        record_id = "capres_123"

    plan = PlanFinalizer(id_factory=lambda: "plan_test", clock=lambda: 1).finalize(
        _draft(),
        capability_snapshot=FakeSnapshot(),
        capability_resolution_record=FakeRecord(),
    )

    assert plan.plan_id == "plan_test"
    assert plan.plan_metadata["capability_snapshot_id"] == "capsnap_123"
    assert plan.plan_metadata["capability_digest"] == "sha256:abc"
    assert plan.plan_metadata["capability_resolution_record_id"] == "capres_123"


def test_plan_finalizer_injects_artifact_refs_and_metadata() -> None:
    plan = PlanFinalizer(clock=lambda: 1).finalize(
        _draft(),
        artifact_refs={"capability_prompt": "artifact_prompt_1", "raw_llm_output": "artifact_raw_1"},
        metadata={"orchestration_stage": "planner"},
    )

    assert plan.plan_metadata["artifact_refs"]["capability_prompt"] == "artifact_prompt_1"
    assert plan.plan_metadata["artifact_refs"]["raw_llm_output"] == "artifact_raw_1"
    assert plan.plan_metadata["orchestration_stage"] == "planner"


def test_plan_finalizer_sets_replan_metadata_and_constraints() -> None:
    plan = PlanFinalizer(clock=lambda: 1).finalize(
        _draft(),
        planner_kind=PlannerKind.RULE_FALLBACK,
        global_constraints={"network": "disabled"},
        parent_plan_id="plan_old",
        revision_no=1,
    )

    assert plan.planner_kind == PlannerKind.RULE_FALLBACK
    assert plan.global_constraints == {"network": "disabled"}
    assert plan.parent_plan_id == "plan_old"
    assert plan.revision_no == 1


def test_plan_finalizer_does_not_mutate_or_canonicalize_step_fields() -> None:
    step = PlanStep(
        step_id="s1",
        title="Run command",
        kind="run_command",
        intent="probe",
        risk_level="LOW",
        on_failure="ABORT",
        inputs={"bad": "payload"},
        required_capabilities=[],
    )
    draft = _draft(step)

    plan = PlanFinalizer(clock=lambda: 1).finalize(draft)

    assert plan.steps[0] is step
    assert plan.steps[0].kind == "run_command"
    assert plan.steps[0].risk_level == "LOW"
    assert plan.steps[0].on_failure == "ABORT"
    assert plan.steps[0].inputs == {"bad": "payload"}
    assert plan.steps[0].required_capabilities == []
