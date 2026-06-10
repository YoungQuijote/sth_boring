from __future__ import annotations

from sdk_test_agent.agent_loop.interaction_decision import InteractionDecision, InteractionDecisionRequest
from sdk_test_agent.agent_loop.preflight import run_preflight
from sdk_test_agent.agent_loop.serializers import to_jsonable
from sdk_test_agent.agent_loop.task_check import TaskCheckRequest
from sdk_test_agent.capability import CapabilitySnapshot
from sdk_test_agent.execution import ExecutionContext
from sdk_test_agent.plan import ExecutionPlan, ExecutionPlanDraft, LlmPlanningContext, PlanContextBase, PlanStep, PlannerInput


def interaction_decision_node(state, runtime):
    raw_user_input = state.get("raw_user_input") or state.get("user_goal", "")
    if runtime.interaction_decider is None:
        decision = InteractionDecision(
            mode="PLAN",
            content="",
            confidence=1.0,
            reason="No interaction decider is configured; preserve the legacy planning route.",
            normalized_goal=raw_user_input,
        )
    else:
        decision = runtime.interaction_decider.decide(
            InteractionDecisionRequest(
                raw_user_input=raw_user_input,
                task_id=state.get("task_id"),
                session_id=state.get("session_id"),
                user_id=state.get("user_id"),
                conversation_summary=state.get("conversation_summary"),
                system_capability_summary=state.get("system_capability_summary"),
                metadata=dict(state.get("metadata", {})),
            )
        )
    update = {"raw_user_input": raw_user_input, "interaction_decision": to_jsonable(decision)}
    if decision.mode == "PLAN":
        update["user_goal"] = decision.normalized_goal
    return update


def build_available_context_keys(bindings) -> tuple[str, ...]:
    keys: list[str] = []
    for key in ("artifact_manager", "runtime_manager", "docker_driver", "command_controller", "package_inspector", "env_inspector"):
        if getattr(bindings, key, None) is not None:
            keys.append(key)
    return tuple(keys)


def env_init_node(state, runtime):
    if runtime.bindings.command_controller is not None:
        runtime.bindings.command_controller.open_session()
    return {"loop_status": "env_initialized", "available_context_keys": list(build_available_context_keys(runtime.bindings))}


def capability_resolve_node(state, runtime):
    cap_input = runtime.metadata.get("capability_input_factory")(state, runtime) if runtime.metadata.get("capability_input_factory") else None
    if cap_input is None:
        from sdk_test_agent.capability import BuildCapabilitySnapshotInput

        cap_input = BuildCapabilitySnapshotInput(
            task_id=state["task_id"],
            task_type=state["task_type"],
            available_context_keys=tuple(state.get("available_context_keys", [])),
            max_risk_level="high",
            allow_placeholder=False,
            allow_deprecated=False,
        )
    snapshot = runtime.capability_panel.build_snapshot(cap_input)
    from sdk_test_agent.capability.schema_renderers import render_capabilities_for_prompt

    prompt = render_capabilities_for_prompt(snapshot)
    return {
        "capability_snapshot_id": snapshot.snapshot_id,
        "capability_digest": snapshot.capability_digest,
        "capability_prompt": prompt,
        "capability_snapshot": snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else to_jsonable(snapshot),
    }


def skill_select_node(state, runtime):
    return {"selected_skill_ids": [], "skill_context": ""}


def plan_node(state, runtime):
    base = PlanContextBase(task_id=state["task_id"], task_type=state["task_type"], goal=state["user_goal"], available_capabilities=list(state.get("capability_snapshot", {}).get("available_step_kinds", [])))
    llm = LlmPlanningContext(user_instruction_raw=state["user_goal"], extra_prompt_vars={"capability_context": state.get("capability_prompt", ""), "capability_snapshot_id": state.get("capability_snapshot_id"), "capability_digest": state.get("capability_digest")})
    draft = runtime.planner.plan(PlannerInput(base_context=base, llm_context=llm))
    return {"draft_plan": to_jsonable(draft)}


def finalize_node(state, runtime):
    draft_cls = runtime.metadata.get("draft_cls")
    draft = _draft_from_dict(state["draft_plan"], draft_cls)
    cap_snap = state.get("capability_snapshot")
    plan = runtime.plan_finalizer.finalize(draft, capability_snapshot=runtime.metadata.get("capability_snapshot_obj") or _capability_snapshot_from_dict(cap_snap))
    return {"plan_id": plan.plan_id, "plan": to_jsonable(plan)}


def validate_node(state, runtime):
    plan = _plan_from_dict(state["plan"], runtime.metadata.get("plan_cls"))
    cap_snap = runtime.metadata.get("capability_snapshot_obj") or _capability_snapshot_from_dict(state.get("capability_snapshot"))
    result = runtime.plan_validator.validate(plan, capability_snapshot=cap_snap)
    return {"validation_result": to_jsonable(result)}


def preflight_node(state, runtime):
    result = run_preflight(plan=state["plan"], execution_registry=runtime.execution_registry, runtime_bindings=runtime.bindings, capability_snapshot=state.get("capability_snapshot"))
    return {"preflight_result": to_jsonable(result)}


def execute_node(state, runtime):
    plan = _plan_from_dict(state["plan"], runtime.metadata.get("plan_cls"))
    run_id = f"run_{state.get('iteration', 0)}"
    exec_ctx = ExecutionContext(task_id=state["task_id"], plan_id=state.get("plan_id", "plan_pending"), run_id=run_id, artifact_manager=runtime.bindings.artifact_manager, runtime_manager=runtime.bindings.runtime_manager, docker_driver=runtime.bindings.docker_driver, command_controller=runtime.bindings.command_controller, package_inspector=runtime.bindings.package_inspector, env_inspector=runtime.bindings.env_inspector)
    result = runtime.execution_engine.run(plan, exec_ctx)
    return {"run_id": run_id, "execution_result": to_jsonable(result)}


def task_check_node(state, runtime):
    req = TaskCheckRequest(task_id=state["task_id"], task_type=state["task_type"], user_goal=state["user_goal"], iteration=int(state.get("iteration", 0)), plan=state.get("plan"), execution_result=state.get("execution_result"), capability_snapshot_id=state.get("capability_snapshot_id"), capability_digest=state.get("capability_digest"), artifact_refs=list(state.get("artifact_refs", [])))
    decision = runtime.task_checker.check(req)
    return {"task_check_decision": decision.to_dict() if hasattr(decision, "to_dict") else to_jsonable(decision)}


def replan_context_node(state, runtime):
    next_iteration = int(state.get("iteration", 0)) + 1
    decision = state.get("task_check_decision", {})
    hint = decision.get("replan_hint") or decision.get("reason")
    return {"iteration": next_iteration, "replan_request": {"reason": hint, "from_iteration": next_iteration - 1}}


def report_node(state, runtime):
    return {"loop_status": "succeeded", "report": {"plan_id": state.get("plan_id"), "run_id": state.get("run_id"), "decision": state.get("task_check_decision")}}


def direct_return_node(state, runtime):
    return {"loop_status": "returned", "response_content": state.get("interaction_decision", {}).get("content", "")}


def refuse_return_node(state, runtime):
    return {"loop_status": "refused", "response_content": state.get("interaction_decision", {}).get("content", "")}


def fail_node(state, runtime):
    return {"loop_status": "failed"}


def human_interrupt_node(state, runtime):
    return {"loop_status": "need_human", "response_content": state.get("interaction_decision", {}).get("content", "")}


def _draft_from_dict(data, draft_cls=None):
    cls = draft_cls or ExecutionPlanDraft
    payload = dict(data)
    payload["steps"] = [step if isinstance(step, PlanStep) else PlanStep(**step) for step in payload.get("steps", [])]
    return cls(**payload)


def _plan_from_dict(data, plan_cls=None):
    if not isinstance(data, dict):
        return data
    cls = plan_cls or ExecutionPlan
    payload = dict(data)
    payload["steps"] = [step if isinstance(step, PlanStep) else PlanStep(**step) for step in payload.get("steps", [])]
    return cls(**payload)


def _capability_snapshot_from_dict(data):
    if data is None or isinstance(data, CapabilitySnapshot):
        return data
    if hasattr(CapabilitySnapshot, "model_validate"):
        return CapabilitySnapshot.model_validate(data)
    return CapabilitySnapshot(**data)
