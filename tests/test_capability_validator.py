from __future__ import annotations

from sdk_test_agent.capability import BuildCapabilitySnapshotInput, CapabilityPanel, CapabilityStatus, CapabilityValidator, build_builtin_capability_registry
from sdk_test_agent.capability.builtin_capabilities import GENERATE_SCRIPT_CAPABILITY, RUN_COMMAND_CAPABILITY
from sdk_test_agent.capability.capability_models import CapabilitySnapshot
from sdk_test_agent.capability.trace_models import CapabilityResolutionRecord


def _copy_model(model, **updates):
    payload = model.model_dump(mode="json")
    payload.update(updates)
    return model.__class__(**payload)


def test_validator_rejects_placeholder_enabled() -> None:
    descriptor = _copy_model(GENERATE_SCRIPT_CAPABILITY, default_enabled=True)
    result = CapabilityValidator().validate_descriptor(descriptor)

    assert result.ok is False
    assert any("placeholder" in issue.message for issue in result.issues)


def test_validator_rejects_bad_example_schema() -> None:
    descriptor = _copy_model(RUN_COMMAND_CAPABILITY, examples=({"step_id": "bad", "kind": "run_command", "inputs": {"command": "date"}},))
    result = CapabilityValidator().validate_descriptor(descriptor)

    assert result.ok is False
    assert any("missing required" in issue.message or "additional" in issue.message for issue in result.issues)


def test_validator_rejects_inconsistent_snapshot_and_record_digest() -> None:
    request = BuildCapabilitySnapshotInput(available_context_keys=("command_controller",))
    panel = CapabilityPanel(build_builtin_capability_registry())
    snapshot, record = panel.build_snapshot_and_record(request)

    bad_snapshot = CapabilitySnapshot(
        **{**snapshot.model_dump(mode="json"), "available_step_kinds": ("wrong",)}
    )
    snapshot_result = CapabilityValidator().validate_snapshot(bad_snapshot)
    assert snapshot_result.ok is False
    assert any(issue.location == "available_step_kinds" for issue in snapshot_result.issues)

    bad_record = CapabilityResolutionRecord(**{**record.model_dump(mode="json"), "output_capability_digest": "sha256:bad"})
    record_result = CapabilityValidator().validate_resolution_record(bad_record, snapshot)
    assert record_result.ok is False
    assert any(issue.location == "output_capability_digest" for issue in record_result.issues)
