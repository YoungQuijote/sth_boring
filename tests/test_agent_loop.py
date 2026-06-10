from __future__ import annotations

import pytest

from sdk_test_agent.agent_loop import (
    InteractionDecision,
    LoopPolicy,
    RuntimeBindings,
    SdkRuntimeContext,
    TaskCheckDecision,
    TaskCheckRequest,
    build_langgraph_agent_loop,
    route_after_interaction_decision,
    route_after_preflight,
    route_after_task_check,
    route_after_validate,
    run_agent_loop_once,
)
from sdk_test_agent.agent_loop.nodes import capability_resolve_node
from sdk_test_agent.agent_loop.task_check import LlmTaskChecker
from sdk_test_agent.capability import CapabilityPanel, build_builtin_capability_registry
from sdk_test_agent.execution.execution_enums import ExecutionRunStatus, ExecutionStepStatus
from sdk_test_agent.execution.execution_models import ExecutionRun, ExecutionRunResult, StepExecutionResult
from sdk_test_agent.plan import ExecutionPlanDraft, PlanFinalizer, PlanValidator
from sdk_test_agent.plan.plan_enums import SUPPORTED_PLAN_STEP_KINDS, ValidationStatus
from sdk_test_agent.plan.plan_models import PlanStep


class FakePlanner:
    def plan(self, planner_input):
        return ExecutionPlanDraft(
            task_id=planner_input.base_context.task_id,
            task_type=planner_input.base_context.task_type,
            goal=planner_input.base_context.goal,
            planner_name="fake",
            planner_version="v1",
            plan_summary="fake plan",
            steps=[
                PlanStep(
                    step_id="s1",
                    title="check time",
                    kind="run_command",
                    intent="check",
                    inputs={"action": "inspect_exec", "payload": {"cmd": ["date"]}},
                    required_capabilities=["cap.run_command.inspect_exec.v1"],
                )
            ],
        )


class FakeExecRegistry:
    def supported_step_kinds(self):
        return {"run_command"}


class FakeCommandController:
    def __init__(self):
        class Disp:
            operators = {"inspect_exec": object()}

        self.dispatcher = Disp()

    def open_session(self):
        return {"opened": True}


class FakeExecutionEngine:
    def run(self, plan, context):
        run = ExecutionRun(run_id=context.run_id, task_id=context.task_id, plan_id=context.plan_id, status=ExecutionRunStatus.SUCCEEDED)
        return ExecutionRunResult(run=run, status=ExecutionRunStatus.SUCCEEDED, step_results={"s1": StepExecutionResult(status=ExecutionStepStatus.SUCCEEDED)})


class FakeInteractionDecider:
    def __init__(self, decision: InteractionDecision):
        self._decision = decision

    def decide(self, request):
        return self._decision


class FakeTaskChecker:
    def __init__(self, decision: TaskCheckDecision):
        self._decision = decision

    def check(self, request: TaskCheckRequest) -> TaskCheckDecision:
        return self._decision


class FakeLlmClient:
    def __init__(self, text: str):
        self.text = text

    def complete(self, request):
        from sdk_test_agent.llm.llm_models import LlmResponse

        return LlmResponse(content=self.text)


def _runtime(task_decision: TaskCheckDecision, interaction_decision: InteractionDecision | None = None):
    bindings = RuntimeBindings(command_controller=FakeCommandController())
    return SdkRuntimeContext(
        bindings=bindings,
        capability_panel=CapabilityPanel(build_builtin_capability_registry()),
        planner=FakePlanner(),
        plan_finalizer=PlanFinalizer(clock=lambda: 1),
        plan_validator=PlanValidator(SUPPORTED_PLAN_STEP_KINDS),
        execution_engine=FakeExecutionEngine(),
        execution_registry=FakeExecRegistry(),
        task_checker=FakeTaskChecker(task_decision),
        loop_policy=LoopPolicy(),
        interaction_decider=FakeInteractionDecider(interaction_decision) if interaction_decision else None,
        metadata={"draft_cls": ExecutionPlanDraft},
    )


def test_route_mappings() -> None:
    assert route_after_interaction_decision({"interaction_decision": {"mode": "PLAN"}}) == "env_init"
    assert route_after_interaction_decision({"interaction_decision": {"mode": "RETURN"}}) == "direct_return"
    assert route_after_validate({"validation_result": {"passed": True}}) == "preflight"
    assert route_after_validate({"validation_result": {"passed": False}}) == "fail"
    assert route_after_preflight({"preflight_result": {"passed": True}}) == "execute"
    assert route_after_preflight({"preflight_result": {"passed": False}}) == "fail"
    assert route_after_task_check({"task_check_decision": {"route": "replan"}}) == "replan_context"


def test_llm_task_checker_parse_success() -> None:
    checker = LlmTaskChecker(FakeLlmClient('{"loop_level":"satisfied","route":"end","confidence":0.9,"reason":"goal met"}'))
    decision = checker.check(TaskCheckRequest(task_id="t1", task_type="sdk", user_goal="goal", iteration=1))
    assert decision.loop_level == "satisfied"
    assert decision.route == "end"


def test_llm_task_checker_malformed_output_fallback() -> None:
    checker = LlmTaskChecker(FakeLlmClient("not json"))
    decision = checker.check(TaskCheckRequest(task_id="t1", task_type="sdk", user_goal="goal", iteration=1))
    assert decision.loop_level == "need_replan"
    assert decision.route == "replan"


def test_capability_resolve_node_outputs_snapshot_fields() -> None:
    runtime = _runtime(TaskCheckDecision(loop_level="satisfied", route="end", confidence=0.9, reason="ok"))
    update = capability_resolve_node({"task_id": "t1", "task_type": "sdk", "available_context_keys": ["command_controller"]}, runtime)
    assert update["capability_snapshot_id"]
    assert update["capability_digest"].startswith("sha256:")
    assert "Available capabilities" in update["capability_prompt"]


def test_procedural_smoke_once() -> None:
    runtime = _runtime(TaskCheckDecision(loop_level="satisfied", route="end", confidence=0.9, reason="done"))
    final = run_agent_loop_once({"task_id": "t1", "task_type": "sdk_deploy", "user_goal": "show utc-8 time", "iteration": 0}, runtime)
    assert final["loop_status"] == "succeeded"
    assert final["validation_result"]["status"] == ValidationStatus.PASSED
    assert final["task_check_decision"]["route"] == "end"


def test_task_check_replan_route() -> None:
    runtime = _runtime(TaskCheckDecision(loop_level="need_replan", route="replan", confidence=0.6, reason="retry"))
    final = run_agent_loop_once({"task_id": "t1", "task_type": "sdk_deploy", "user_goal": "retry", "iteration": 0}, runtime)
    assert final["iteration"] == 1
    assert final["replan_request"]["reason"] == "retry"


def test_langgraph_adapter_smoke_or_skip() -> None:
    runtime = _runtime(TaskCheckDecision(loop_level="satisfied", route="end", confidence=0.9, reason="done"))
    try:
        graph = build_langgraph_agent_loop(runtime)
    except RuntimeError:
        pytest.skip("langgraph not installed")
    out = graph.invoke({"task_id": "t1", "task_type": "sdk_deploy", "user_goal": "utc", "iteration": 0})
    assert out["task_check_decision"]["route"] in {"end", "replan", "fail", "ask_input", "human_interrupt"}


def test_direct_return_skips_planner_chain() -> None:
    interaction = InteractionDecision(mode="RETURN", content="你好！", confidence=0.9, reason="greeting")
    runtime = _runtime(TaskCheckDecision(loop_level="satisfied", route="end", confidence=0.9, reason="unused"), interaction)
    final = run_agent_loop_once({"task_id": "t1", "task_type": "chat", "raw_user_input": "你好"}, runtime)
    assert final["loop_status"] == "returned"
    assert final["response_content"] == "你好！"
    assert "draft_plan" not in final


def test_plan_route_preserves_raw_input_and_uses_normalized_goal() -> None:
    interaction = InteractionDecision(mode="PLAN", content="planning", confidence=0.9, reason="task", normalized_goal="show time")
    runtime = _runtime(TaskCheckDecision(loop_level="satisfied", route="end", confidence=0.9, reason="done"), interaction)
    final = run_agent_loop_once({"task_id": "t1", "task_type": "sdk", "raw_user_input": "please show time"}, runtime)
    assert final["raw_user_input"] == "please show time"
    assert final["user_goal"] == "show time"
    assert final["loop_status"] == "succeeded"


@pytest.mark.parametrize(
    ("mode", "expected_status"),
    [("REFUSE", "refused"), ("HUMAN", "need_human")],
)
def test_non_plan_terminal_routes(mode: str, expected_status: str) -> None:
    interaction = InteractionDecision(mode=mode, content="stop here", confidence=0.9, reason="terminal")
    runtime = _runtime(TaskCheckDecision(loop_level="satisfied", route="end", confidence=0.9, reason="unused"), interaction)
    final = run_agent_loop_once({"task_id": "t1", "task_type": "chat", "raw_user_input": "request"}, runtime)
    assert final["loop_status"] == expected_status
    assert final["response_content"] == "stop here"
    assert "draft_plan" not in final
