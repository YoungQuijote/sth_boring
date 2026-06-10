from __future__ import annotations

import pytest

from sdk_test_agent.capability import CapabilityRegistry, build_builtin_capability_registry
from sdk_test_agent.capability.builtin_capabilities import RUN_COMMAND_CAPABILITY


def test_builtin_registry_registers_expected_capabilities() -> None:
    registry = build_builtin_capability_registry()

    assert registry.get_by_id("cap.run_command.inspect_exec.v1").step_kind == "run_command"
    assert registry.get_by_step_kind("run_command").capability_id == "cap.run_command.inspect_exec.v1"
    assert "run_command" in registry.available_step_kinds()
    assert len(registry.list_all()) >= 11


def test_duplicate_capability_id_raises() -> None:
    registry = CapabilityRegistry()
    registry.register(RUN_COMMAND_CAPABILITY)

    with pytest.raises(ValueError, match="duplicated capability_id"):
        registry.register(RUN_COMMAND_CAPABILITY)


def test_duplicate_step_kind_raises() -> None:
    registry = CapabilityRegistry()
    first = RUN_COMMAND_CAPABILITY
    second = first.model_copy(update={"capability_id": "cap.other.run_command.v1"}) if hasattr(first, "model_copy") else first.__class__(**{**first.model_dump(), "capability_id": "cap.other.run_command.v1"})
    registry.register(first)

    with pytest.raises(ValueError, match="duplicated step_kind"):
        registry.register(second)
