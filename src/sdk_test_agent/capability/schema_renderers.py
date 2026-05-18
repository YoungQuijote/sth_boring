from __future__ import annotations

import json
from typing import Any

from .capability_enums import CapabilityStatus, CapabilityVisibility
from .capability_models import CapabilitySnapshot


def render_capabilities_for_prompt(snapshot: CapabilitySnapshot) -> str:
    availability_by_id = {a.capability_id: a for a in snapshot.availability}
    lines: list[str] = ["Available capabilities:", ""]
    enabled = [d for d in snapshot.capabilities if availability_by_id[d.capability_id].status == CapabilityStatus.ENABLED]
    for idx, descriptor in enumerate(enabled, start=1):
        lines.extend(
            [
                f"{idx}. {descriptor.step_kind}",
                f"   Capability ID: {descriptor.capability_id}",
                f"   Description: {descriptor.description}",
                f"   Risk: {descriptor.risk_level.value if hasattr(descriptor.risk_level, 'value') else descriptor.risk_level}",
                f"   Required context keys: {', '.join(descriptor.required_context_keys) or '(none)'}",
                "   Input schema:",
                _indent(json.dumps(descriptor.input_schema, ensure_ascii=False, sort_keys=True), "   "),
            ]
        )
        if descriptor.examples:
            lines.extend(["   Example:", _indent(json.dumps(descriptor.examples[0], ensure_ascii=False, sort_keys=True), "   ")])
        lines.append("")

    lines.extend(["Unavailable capabilities:", ""])
    unavailable = [d for d in snapshot.capabilities if availability_by_id[d.capability_id].status != CapabilityStatus.ENABLED]
    if not unavailable:
        lines.append("- (none)")
    for descriptor in unavailable:
        availability = availability_by_id[descriptor.capability_id]
        reason = availability.reason or availability.status.value
        lines.append(f"- {descriptor.step_kind}: {reason}")
    return "\n".join(lines).rstrip()


def render_input_schema_map(snapshot: CapabilitySnapshot) -> dict[str, dict[str, Any]]:
    availability_by_id = {a.capability_id: a for a in snapshot.availability}
    return {
        d.step_kind: d.input_schema
        for d in snapshot.capabilities
        if availability_by_id[d.capability_id].status == CapabilityStatus.ENABLED and d.visibility == CapabilityVisibility.PLANNER_VISIBLE
    }


def render_snapshot_as_json(snapshot: CapabilitySnapshot) -> str:
    return json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, default=str)


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())
