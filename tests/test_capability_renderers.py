from __future__ import annotations

from sdk_test_agent.capability import (
    BuildCapabilitySnapshotInput,
    CapabilityPanel,
    build_builtin_capability_registry,
    render_capabilities_for_prompt,
    render_input_schema_map,
    render_snapshot_as_json,
)


def test_prompt_renderer_contains_capabilities_schema_and_unavailable_markers() -> None:
    snapshot = CapabilityPanel(build_builtin_capability_registry()).build_snapshot(
        BuildCapabilitySnapshotInput(available_context_keys=("command_controller",))
    )

    text = render_capabilities_for_prompt(snapshot)

    assert "run_command" in text
    assert "Input schema" in text
    assert "payload" in text
    assert "generate_script" in text
    assert "placeholder" in text


def test_input_schema_map_contains_only_enabled_planner_visible_capabilities() -> None:
    snapshot = CapabilityPanel(build_builtin_capability_registry()).build_snapshot(
        BuildCapabilitySnapshotInput(available_context_keys=("command_controller",))
    )
    schema_map = render_input_schema_map(snapshot)

    assert set(schema_map) == {"run_command", "execute_probe"}
    assert "payload" in schema_map["run_command"].get("properties", {})
    assert "generate_script" not in schema_map
    assert "run_command" in render_snapshot_as_json(snapshot)


def test_llm_planner_prompt_can_include_capability_context() -> None:
    from sdk_test_agent.plan.plan_context import LlmPlanningContext, PlanContextBase, PlannerInput
    from sdk_test_agent.plan.planners.llm_planner import LlmPlanner

    base = PlanContextBase(task_id="task_1", task_type="sdk_deploy", goal="deploy")
    llm = LlmPlanningContext(user_instruction_raw="plan", extra_prompt_vars={"capability_context": "run_command schema here"})

    prompt = LlmPlanner(llm_client=object())._build_prompt(PlannerInput(base_context=base, llm_context=llm))

    assert "Capability context" in prompt
    assert "run_command schema here" in prompt
