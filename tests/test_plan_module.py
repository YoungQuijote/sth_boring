from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from sdk_test_agent.llm.llm_models import LlmResponse
from sdk_test_agent.plan import PlanContextBase, PlannerInput
from sdk_test_agent.plan.plan_enums import SUPPORTED_PLAN_STEP_KINDS, PlanStepKind, StepFailurePolicy, StepRiskLevel, ValidationStatus
from sdk_test_agent.plan.plan_errors import PlanLlmClientNotConfiguredError
from sdk_test_agent.plan.plan_memory import InMemoryPlanMemoryStore
from sdk_test_agent.plan.plan_models import ExecutionPlan, ExecutionPlanDraft, PlanStep
from sdk_test_agent.plan.plan_validation import PlanValidator
from sdk_test_agent.plan.planners.demo_java_planner import DemoJavaPlanner
from sdk_test_agent.plan.planners.fast_planner import FastPlanner
from sdk_test_agent.plan.planners.llm_planner import LlmPlanner


ALL_CAPS = {
    "inspection.package.java",
    "docker.build_image",
    "runtime.create_container",
    "inspection.env.docker",
    "artifact.collect",
}


def _context() -> PlanContextBase:
    return PlanContextBase(
        task_id="task_demo",
        task_type="sdk_deploy",
        goal="Deploy Java SDK jar and verify runtime environment.",
        available_capabilities=sorted(ALL_CAPS),
    )


def test_plan_model_serialization() -> None:
    step = PlanStep(step_id="s1", title="inspect", kind=PlanStepKind.INSPECT_PACKAGE, intent="inspect package")
    plan = ExecutionPlan(
        plan_id="plan1",
        task_id="task1",
        task_type="sdk_deploy",
        goal="deploy",
        planner_kind="demo",
        planner_name="demo",
        planner_version="0.1.0",
        status="validated",
        steps=[step],
    )

    raw = json.dumps(asdict(plan))
    assert "inspect_package" in raw


def test_demo_java_planner_smoke_and_validation() -> None:
    planner = DemoJavaPlanner()
    plan = planner.plan(PlannerInput(base_context=_context()))

    kinds = {s.kind for s in plan.steps}
    assert PlanStepKind.BUILD_IMAGE in kinds
    assert PlanStepKind.CREATE_RUNTIME in kinds
    assert PlanStepKind.INSPECT_ENVIRONMENT in kinds
    assert len({s.step_id for s in plan.steps}) == len(plan.steps)

    result = PlanValidator(SUPPORTED_PLAN_STEP_KINDS, available_capabilities=ALL_CAPS).validate(plan)
    assert result.passed is True


def test_plan_validator_failure_cases() -> None:
    validator = PlanValidator({PlanStepKind.INSPECT_PACKAGE}, available_capabilities={"cap"}, max_step_count=2)
    empty = ExecutionPlanDraft(
        task_id="t",
        task_type="sdk_deploy",
        goal="g",
        planner_name="p",
        planner_version="v",
        plan_summary="empty",
        steps=[],
    )
    assert validator.validate(empty).status == ValidationStatus.FAILED

    bad = ExecutionPlanDraft(
        task_id="t",
        task_type="sdk_deploy",
        goal="g",
        planner_name="p",
        planner_version="v",
        plan_summary="bad",
        steps=[
            PlanStep(
                step_id="dup",
                title="a",
                kind=PlanStepKind.BUILD_IMAGE,
                intent="x",
                required_capabilities=["missing"],
                risk_level="bad-risk",
                on_failure="bad-policy",
            ),
            PlanStep(
                step_id="dup",
                title="b",
                kind=PlanStepKind.INSPECT_PACKAGE,
                intent="x",
                depends_on=["missing_step"],
            ),
        ],
    )
    result = validator.validate(bad)
    assert result.status == ValidationStatus.FAILED
    codes = {i.code for i in result.issues}
    assert "step.id.duplicate" in codes
    assert "step.depends_on.missing" in codes
    assert "step.kind.unsupported" in codes
    assert "step.capability.missing" in codes


def test_fast_planner_memory_recall() -> None:
    store = InMemoryPlanMemoryStore()
    fast = FastPlanner(store)
    ctx = _context()
    assert fast.retrieve(ctx) == []

    plan = DemoJavaPlanner().plan(PlannerInput(base_context=ctx))
    store.save_successful_plan(ctx.task_id, ctx.task_type, ctx.goal, plan, success_score=0.95)
    recalled = fast.retrieve(ctx)
    assert len(recalled) == 1
    draft = fast.plan(PlannerInput(base_context=ctx))
    assert draft is not None
    assert draft.steps


def test_llm_planner_no_client() -> None:
    with pytest.raises(PlanLlmClientNotConfiguredError):
        LlmPlanner().plan(PlannerInput(base_context=_context()))


class FakeLlmClient:
    def complete(self, request):
        return LlmResponse(
            content=json.dumps(
                {
                    "plan_summary": "demo",
                    "steps": [
                        {
                            "step_id": "step_001",
                            "title": "Inspect",
                            "kind": "inspect_package",
                            "intent": "inspect package",
                            "depends_on": [],
                            "inputs": {},
                            "expected_outputs": [],
                            "required_capabilities": [],
                            "timeout_sec": 10,
                            "retryable": False,
                            "optional": False,
                            "risk_level": StepRiskLevel.LOW,
                            "on_failure": StepFailurePolicy.ABORT,
                        }
                    ],
                    "assumptions": [],
                    "missing_information": [],
                    "risk_notes": [],
                }
            )
        )


def test_llm_planner_with_fake_client() -> None:
    draft = LlmPlanner(llm_client=FakeLlmClient()).plan(PlannerInput(base_context=_context()))
    assert draft.plan_summary == "demo"
    assert draft.steps[0].kind == PlanStepKind.INSPECT_PACKAGE
