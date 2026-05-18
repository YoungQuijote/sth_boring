from __future__ import annotations

from ._pydantic_compat import BaseModel, ConfigDict, Field
from .capability_enums import CapabilityStatus, CapabilityVisibility
from .capability_models import CapabilityDescriptor, CapabilitySnapshot
from .capability_panel import CapabilityPanel
from .capability_registry import CapabilityRegistry
from .schema_validation import validate_payload_against_schema
from .trace_models import CapabilityResolutionRecord


class CapabilityValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    location: str
    message: str


class CapabilityValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    issues: list[CapabilityValidationIssue] = Field(default_factory=list)


class CapabilityValidator:
    def validate_descriptor(self, descriptor: CapabilityDescriptor) -> CapabilityValidationResult:
        issues: list[CapabilityValidationIssue] = []
        if not descriptor.capability_id:
            issues.append(self._issue("error", "capability_id", "capability_id must not be empty"))
        if not descriptor.version:
            issues.append(self._issue("error", "version", "version must not be empty"))
        if not descriptor.step_kind:
            issues.append(self._issue("error", "step_kind", "step_kind must not be empty"))
        if descriptor.is_placeholder and descriptor.default_enabled:
            issues.append(self._issue("error", descriptor.capability_id, "placeholder capability must default_enabled=False"))
        if descriptor.is_deprecated and descriptor.visibility == CapabilityVisibility.PLANNER_VISIBLE:
            issues.append(self._issue("warning", descriptor.capability_id, "deprecated capability is planner-visible"))
        for idx, example in enumerate(descriptor.examples):
            inputs = example.get("inputs", {})
            errors = validate_payload_against_schema(inputs, descriptor.input_schema)
            for error in errors:
                issues.append(self._issue("error", f"{descriptor.capability_id}.examples[{idx}].inputs", error))
        return self._result(issues)

    def validate_registry(self, registry: CapabilityRegistry) -> CapabilityValidationResult:
        issues: list[CapabilityValidationIssue] = []
        for descriptor in registry.list_all():
            issues.extend(self.validate_descriptor(descriptor).issues)
        return self._result(issues)

    def validate_snapshot(self, snapshot: CapabilitySnapshot) -> CapabilityValidationResult:
        issues: list[CapabilityValidationIssue] = []
        enabled = tuple(a.step_kind for a in snapshot.availability if a.status == CapabilityStatus.ENABLED)
        unavailable = tuple(a.step_kind for a in snapshot.availability if a.status != CapabilityStatus.ENABLED)
        if tuple(snapshot.available_step_kinds) != enabled:
            issues.append(self._issue("error", "available_step_kinds", "available_step_kinds must match enabled availability records"))
        if tuple(snapshot.unavailable_step_kinds) != unavailable:
            issues.append(self._issue("error", "unavailable_step_kinds", "unavailable_step_kinds must match non-enabled availability records"))
        digest = CapabilityPanel.recompute_digest(snapshot)
        if digest != snapshot.capability_digest:
            issues.append(self._issue("error", "capability_digest", "capability_digest does not match recomputed digest"))
        return self._result(issues)

    def validate_resolution_record(self, record: CapabilityResolutionRecord, snapshot: CapabilitySnapshot | None = None) -> CapabilityValidationResult:
        issues: list[CapabilityValidationIssue] = []
        if snapshot is not None:
            if record.output_snapshot_id != snapshot.snapshot_id:
                issues.append(self._issue("error", "output_snapshot_id", "record snapshot id does not match snapshot"))
            if record.output_capability_digest != snapshot.capability_digest:
                issues.append(self._issue("error", "output_capability_digest", "record digest does not match snapshot digest"))
        by_status = {status.value: [] for status in CapabilityStatus}
        for availability in record.availability_records:
            by_status[str(availability.get("status"))].append(availability.get("capability_id"))
        checks = {
            "enabled_capability_ids": (record.enabled_capability_ids, by_status[CapabilityStatus.ENABLED.value]),
            "disabled_capability_ids": (record.disabled_capability_ids, by_status[CapabilityStatus.DISABLED.value]),
            "unavailable_capability_ids": (record.unavailable_capability_ids, by_status[CapabilityStatus.UNAVAILABLE.value]),
            "placeholder_capability_ids": (record.placeholder_capability_ids, by_status[CapabilityStatus.PLACEHOLDER.value]),
            "deprecated_capability_ids": (record.deprecated_capability_ids, by_status[CapabilityStatus.DEPRECATED.value]),
        }
        for location, (actual, expected) in checks.items():
            if sorted(actual) != sorted(expected):
                issues.append(self._issue("error", location, f"{location} is not consistent with availability_records"))
        return self._result(issues)

    @staticmethod
    def _issue(level: str, location: str, message: str) -> CapabilityValidationIssue:
        return CapabilityValidationIssue(level=level, location=location, message=message)

    @staticmethod
    def _result(issues: list[CapabilityValidationIssue]) -> CapabilityValidationResult:
        return CapabilityValidationResult(ok=not any(issue.level == "error" for issue in issues), issues=issues)
