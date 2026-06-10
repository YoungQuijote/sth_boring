from __future__ import annotations

from sdk_test_agent.agent_loop.nodes import (
    capability_resolve_node,
    direct_return_node,
    env_init_node,
    execute_node,
    fail_node,
    finalize_node,
    human_interrupt_node,
    interaction_decision_node,
    plan_node,
    preflight_node,
    refuse_return_node,
    replan_context_node,
    report_node,
    skill_select_node,
    task_check_node,
    validate_node,
)


def route_after_interaction_decision(state):
    mode = state.get("interaction_decision", {}).get("mode")
    return {
        "PLAN": "env_init",
        "RETURN": "direct_return",
        "REFUSE": "refuse_return",
        "HUMAN": "human_interrupt",
    }.get(mode, "fail")


def route_after_validate(state):
    result = state.get("validation_result", {})
    return "preflight" if result.get("passed") is True or result.get("status") == "passed" else "fail"


def route_after_preflight(state):
    result = state.get("preflight_result", {})
    return "execute" if result.get("passed") is True else "fail"


def route_after_task_check(state):
    route = state.get("task_check_decision", {}).get("route")
    if route == "end":
        return "report"
    if route == "replan":
        return "replan_context"
    if route == "human_interrupt":
        return "human_interrupt"
    return "fail"


def build_langgraph_agent_loop(runtime_context):
    try:
        from langgraph.graph import END, START, StateGraph
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("langgraph is not installed") from exc

    builder = StateGraph(dict)
    nodes = {
        "interaction_decision": interaction_decision_node,
        "env_init": env_init_node,
        "capability_resolve": capability_resolve_node,
        "skill_select": skill_select_node,
        "plan": plan_node,
        "finalize": finalize_node,
        "validate": validate_node,
        "preflight": preflight_node,
        "execute": execute_node,
        "task_check": task_check_node,
        "replan_context": replan_context_node,
        "report": report_node,
        "direct_return": direct_return_node,
        "refuse_return": refuse_return_node,
        "fail": fail_node,
        "human_interrupt": human_interrupt_node,
    }
    for name, node in nodes.items():
        builder.add_node(name, lambda state, node=node: node(state, runtime_context))

    builder.add_edge(START, "interaction_decision")
    builder.add_conditional_edges("interaction_decision", route_after_interaction_decision)
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
    for terminal in ("report", "direct_return", "refuse_return", "fail", "human_interrupt"):
        builder.add_edge(terminal, END)
    return builder.compile()


def run_agent_loop_once(state: dict, runtime_context):
    s = dict(state)
    s.update(interaction_decision_node(s, runtime_context))
    interaction_route = route_after_interaction_decision(s)
    if interaction_route != "env_init":
        terminal = {
            "direct_return": direct_return_node,
            "refuse_return": refuse_return_node,
            "human_interrupt": human_interrupt_node,
        }.get(interaction_route, fail_node)
        s.update(terminal(s, runtime_context))
        return s

    for fn in (env_init_node, capability_resolve_node, skill_select_node, plan_node, finalize_node, validate_node):
        s.update(fn(s, runtime_context))
    if route_after_validate(s) != "preflight":
        s.update(fail_node(s, runtime_context))
        return s
    s.update(preflight_node(s, runtime_context))
    if route_after_preflight(s) != "execute":
        s.update(fail_node(s, runtime_context))
        return s
    for fn in (execute_node, task_check_node):
        s.update(fn(s, runtime_context))
    route = route_after_task_check(s)
    terminal = {
        "report": report_node,
        "replan_context": replan_context_node,
        "human_interrupt": human_interrupt_node,
    }.get(route, fail_node)
    s.update(terminal(s, runtime_context))
    return s
