from __future__ import annotations

from sdk_test_agent.capability import BuildCapabilitySnapshotInput, CapabilityPanel, CapabilityStatus, build_builtin_capability_registry
from sdk_test_agent.capability.capability_enums import CapabilityRiskLevel


def _snapshot(**kwargs):
    registry = build_builtin_capability_registry()
    request = BuildCapabilitySnapshotInput(**kwargs)
    return CapabilityPanel(registry).build_snapshot(request)


def test_panel_marks_placeholder_unavailable_and_context_missing() -> None:
    snapshot = _snapshot(available_context_keys=("command_controller",), max_risk_level=CapabilityRiskLevel.MEDIUM)
    by_kind = {a.step_kind: a for a in snapshot.availability}

    assert by_kind["generate_script"].status == CapabilityStatus.PLACEHOLDER
    assert by_kind["inspect_package"].status == CapabilityStatus.UNAVAILABLE
    assert by_kind["inspect_package"].missing_context_keys == ("package_inspector",)
    assert "run_command" in snapshot.available_step_kinds
    assert "inspect_package" in snapshot.unavailable_step_kinds


def test_panel_risk_and_forbidden_policy() -> None:
    snapshot = _snapshot(
        available_context_keys=("command_controller", "docker_driver"),
        forbidden_capability_ids=("cap.run_command.inspect_exec.v1",),
        max_risk_level=CapabilityRiskLevel.LOW,
    )
    by_kind = {a.step_kind: a for a in snapshot.availability}

    assert by_kind["run_command"].status == CapabilityStatus.DISABLED
    assert by_kind["run_command"].blocked_by_skill is True
    assert by_kind["build_image"].status == CapabilityStatus.DISABLED
    assert by_kind["build_image"].blocked_by_policy is True


def test_panel_digest_is_stable_and_recomputable_for_same_resolution_inputs() -> None:
    request = BuildCapabilitySnapshotInput(available_context_keys=("command_controller",), max_risk_level=CapabilityRiskLevel.MEDIUM)
    panel = CapabilityPanel(build_builtin_capability_registry())
    first = panel.build_snapshot(request)
    second = panel.build_snapshot(request)

    assert first.capability_digest == second.capability_digest
    assert CapabilityPanel.recompute_digest(first) == first.capability_digest


def test_panel_builds_resolution_record() -> None:
    request = BuildCapabilitySnapshotInput(task_id="task_1", available_context_keys=("command_controller",))
    panel = CapabilityPanel(build_builtin_capability_registry())
    snapshot, record = panel.build_snapshot_and_record(request)

    assert record.action_name == "capability.build_snapshot"
    assert record.output_snapshot_id == snapshot.snapshot_id
    assert record.output_capability_digest == snapshot.capability_digest
    assert "cap.run_command.inspect_exec.v1" in record.enabled_capability_ids
