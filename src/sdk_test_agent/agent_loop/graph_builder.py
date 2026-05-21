from __future__ import annotations

from sdk_test_agent.agent_loop.nodes import (
    capability_resolve_node,
    env_init_node,
    execute_node,
    fail_node,
    finalize_node,
    human_interrupt_node,
    plan_node,
    preflight_node,
    replan_context_node,
    report_node,
    skill_select_node,
    task_check_node,
    validate_node,
)


def route_after_validate(state):
    result = state.get("validation_result", {})
    if result.get("passed") is True:
        return "preflight"
    return "fail"


def route_after_preflight(state):
    result = state.get("preflight_result", {})
    return "execute" if result.get("passed") is True else "fail"


def route_after_task_check(state):
    decision = state.get("task_check_decision", {})
    route = decision.get("route")
    if route == "end":
        return "report"
    if route == "replan":
        return "replan_context"
    if route == "ask_input":
        return "fail"
    if route == "human_interrupt":
        return "human_interrupt"
    return "fail"


def build_langgraph_agent_loop(runtime_context):
    try:
        from langgraph.graph import END, START, StateGraph
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("langgraph is not installed") from exc

    builder = StateGraph(dict)

    builder.add_node("env_init", lambda state: env_init_node(state, runtime_context))
    builder.add_node("capability_resolve", lambda state: capability_resolve_node(state, runtime_context))
    builder.add_node("skill_select", lambda state: skill_select_node(state, runtime_context))
    builder.add_node("plan", lambda state: plan_node(state, runtime_context))
    builder.add_node("finalize", lambda state: finalize_node(state, runtime_context))
    builder.add_node("validate", lambda state: validate_node(state, runtime_context))
    builder.add_node("preflight", lambda state: preflight_node(state, runtime_context))
    builder.add_node("execute", lambda state: execute_node(state, runtime_context))
    builder.add_node("task_check", lambda state: task_check_node(state, runtime_context))
    builder.add_node("replan_context", lambda state: replan_context_node(state, runtime_context))
    builder.add_node("report", lambda state: report_node(state, runtime_context))
    builder.add_node("fail", lambda state: fail_node(state, runtime_context))
    builder.add_node("human_interrupt", lambda state: human_interrupt_node(state, runtime_context))

    builder.add_edge(START, "env_init")
    builder.add_edge("env_init", "capability_resolve")
    builder.add_edge("capability_resolve", "skill_select")
    builder.add_edge("skill_select", "plan")
    builder.add_edge("plan", "finalize")
    builder.add_edge("finalize", "validate")
    builder.add_conditional_edges("validate", route_after_validate)
    builder.add_conditional_edges("preflight", route_after_preflight)
    builder.add_edge("execute", "task_check")
    builder.add_conditional_edges("task_check", route_after_task_check)
    builder.add_edge("replan_context", "capability_resolve")
    builder.add_edge("report", END)
    builder.add_edge("fail", END)
    builder.add_edge("human_interrupt", END)
    return builder.compile()


def run_agent_loop_once(state: dict, runtime_context):
    s = dict(state)
    for fn in (env_init_node, capability_resolve_node, skill_select_node, plan_node, finalize_node, validate_node, preflight_node, execute_node, task_check_node):
        s.update(fn(s, runtime_context))
    route = route_after_task_check(s)
    if route == "report":
        s.update(report_node(s, runtime_context))
    elif route == "replan_context":
        s.update(replan_context_node(s, runtime_context))
    elif route == "human_interrupt":
        s.update(human_interrupt_node(s, runtime_context))
    else:
        s.update(fail_node(s, runtime_context))
    return s
