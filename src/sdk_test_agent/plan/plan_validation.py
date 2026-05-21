from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sdk_test_agent.capability.capability_enums import CapabilityStatus
from sdk_test_agent.capability.capability_models import CapabilitySnapshot
from sdk_test_agent.capability.capability_registry import CapabilityRegistry
from sdk_test_agent.capability.schema_validation import validate_payload_against_schema

from .plan_enums import (
    SUPPORTED_PLAN_STEP_KINDS,
    VALID_FAILURE_POLICIES,
    VALID_RISK_LEVELS,
    StepRiskLevel,
    ValidationSeverity,
    ValidationStatus,
)
from .plan_models import ExecutionPlan, ExecutionPlanDraft, PlanStep


@dataclass(slots=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    step_id: str | None = None
    step_kind: str | None = None
    path: str | None = None


@dataclass(slots=True)
class PlanValidationResult:
    status: str
    issues: list[ValidationIssue] = field(default_factory=list)
    checked_at: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]


class PlanValidator:
    def __init__(
        self,
        supported_step_kinds: set[str] | None = None,
        available_capabilities: set[str] | None = None,
        max_step_count: int | None = None,
        capability_registry: CapabilityRegistry | None = None,
        *,
        strict_required_capabilities: bool = False,
        require_capability_digest: bool = False,
        fail_on_warning: bool = False,
        allow_deprecated_capability: bool = False,
    ) -> None:
        self.supported_step_kinds = supported_step_kinds or set(SUPPORTED_PLAN_STEP_KINDS)
        self.available_capabilities = available_capabilities
        self.max_step_count = max_step_count
        self.capability_registry = capability_registry
        self.strict_required_capabilities = strict_required_capabilities
        self.require_capability_digest = require_capability_digest
        self.fail_on_warning = fail_on_warning
        self.allow_deprecated_capability = allow_deprecated_capability

    def validate(self, plan: ExecutionPlan | ExecutionPlanDraft, capability_snapshot: CapabilitySnapshot | None = None) -> PlanValidationResult:
        issues: list[ValidationIssue] = []
        steps = list(plan.steps or [])
        if not steps:
            issues.append(self._issue("PLAN_EMPTY_STEPS", ValidationSeverity.ERROR, "plan must contain at least one step"))
            issues.append(self._issue("plan.steps.empty", ValidationSeverity.ERROR, "plan must contain at least one step"))
            return self._result(issues, capability_snapshot=capability_snapshot)

        if self.max_step_count is not None and len(steps) > self.max_step_count:
            issues.append(
                self._issue(
                    "PLAN_TOO_MANY_STEPS",
                    ValidationSeverity.ERROR,
                    f"plan has {len(steps)} steps, max is {self.max_step_count}",
                    path="steps",
                )
            )

        seen: set[str] = set()
        for idx, step in enumerate(steps):
            loc = f"steps[{idx}]"
            if not step.step_id:
                issues.append(self._issue("PLAN_STEP_ID_EMPTY", ValidationSeverity.ERROR, "step_id is required", loc, step=step))
                issues.append(self._issue("step.id.empty", ValidationSeverity.ERROR, "step_id is required", loc, step=step))
            if step.step_id in seen:
                issues.append(self._issue("PLAN_DUPLICATE_STEP_ID", ValidationSeverity.ERROR, f"duplicate step_id {step.step_id}", loc, step=step))
                issues.append(self._issue("step.id.duplicate", ValidationSeverity.ERROR, f"duplicate step_id {step.step_id}", loc, step=step))
            seen.add(step.step_id)

        if capability_snapshot is not None:
            issues.extend(self._validate_capability_digest(plan, capability_snapshot))
            snapshot_index = self._build_snapshot_index(capability_snapshot)
        else:
            snapshot_index = None

        known = {s.step_id for s in steps}
        for idx, step in enumerate(steps):
            issues.extend(self._validate_step_base(step, idx, known))
            if capability_snapshot is not None and snapshot_index is not None:
                issues.extend(self._validate_step_against_capability_snapshot(step, idx, snapshot_index))
            elif self.capability_registry is not None:
                issues.extend(self._validate_step_against_registry(step, idx))

        return self._result(issues, capability_snapshot=capability_snapshot)

    def _validate_step_base(self, step: PlanStep, idx: int, known_step_ids: set[str]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        loc = f"steps[{idx}]"
        for dep in step.depends_on:
            if dep not in known_step_ids:
                issues.append(self._issue("PLAN_UNKNOWN_DEPENDENCY", ValidationSeverity.ERROR, f"unknown dependency {dep}", loc, step=step, path=f"{loc}.depends_on"))
                issues.append(self._issue("step.depends_on.missing", ValidationSeverity.ERROR, f"unknown dependency {dep}", loc, step=step))
        if not step.kind:
            issues.append(self._issue("PLAN_STEP_KIND_EMPTY", ValidationSeverity.ERROR, "step.kind is required", loc, step=step, path=f"{loc}.kind"))
        elif step.kind not in self.supported_step_kinds:
            issues.append(self._issue("PLAN_UNSUPPORTED_STEP_KIND", ValidationSeverity.ERROR, f"unsupported step kind {step.kind}", loc, step=step, path=f"{loc}.kind"))
            issues.append(self._issue("step.kind.unsupported", ValidationSeverity.ERROR, f"unsupported step kind {step.kind}", loc, step=step))
        if self.available_capabilities is not None:
            for cap in step.required_capabilities:
                if cap not in self.available_capabilities:
                    issues.append(self._issue("step.capability.missing", ValidationSeverity.ERROR, f"missing capability {cap}", loc, step=step))
        if step.risk_level not in VALID_RISK_LEVELS:
            issues.append(self._issue("PLAN_INVALID_RISK_LEVEL", ValidationSeverity.ERROR, f"invalid risk_level {step.risk_level}", loc, step=step, path=f"{loc}.risk_level"))
            issues.append(self._issue("step.risk.invalid", ValidationSeverity.ERROR, f"invalid risk_level {step.risk_level}", loc, step=step))
        if step.risk_level == StepRiskLevel.HIGH:
            issues.append(self._issue("step.risk.high", ValidationSeverity.WARNING, "high risk step requires review", loc, step=step))
        if step.on_failure not in VALID_FAILURE_POLICIES:
            issues.append(self._issue("PLAN_INVALID_ON_FAILURE", ValidationSeverity.ERROR, f"invalid on_failure {step.on_failure}", loc, step=step, path=f"{loc}.on_failure"))
            issues.append(self._issue("step.on_failure.invalid", ValidationSeverity.ERROR, f"invalid on_failure {step.on_failure}", loc, step=step))
        if step.timeout_sec is not None and step.timeout_sec <= 0:
            issues.append(self._issue("PLAN_INVALID_TIMEOUT", ValidationSeverity.ERROR, "timeout_sec must be positive", loc, step=step, path=f"{loc}.timeout_sec"))
        return issues

    def _validate_capability_digest(self, plan: ExecutionPlan | ExecutionPlanDraft, snapshot: CapabilitySnapshot) -> list[ValidationIssue]:
        metadata = getattr(plan, "plan_metadata", {}) or {}
        digest = metadata.get("capability_digest")
        if not digest:
            severity = ValidationSeverity.ERROR if self.require_capability_digest else ValidationSeverity.WARNING
            return [
                self._issue(
                    "CAPABILITY_DIGEST_MISSING",
                    severity,
                    "plan_metadata.capability_digest is missing",
                    path="plan_metadata.capability_digest",
                    metadata={"snapshot_digest": snapshot.capability_digest},
                )
            ]
        if digest != snapshot.capability_digest:
            return [
                self._issue(
                    "CAPABILITY_DIGEST_MISMATCH",
                    ValidationSeverity.ERROR,
                    "plan capability_digest does not match capability snapshot",
                    path="plan_metadata.capability_digest",
                    metadata={"plan_digest": digest, "snapshot_digest": snapshot.capability_digest},
                )
            ]
        return []

    @staticmethod
    def _build_snapshot_index(snapshot: CapabilitySnapshot) -> dict[str, Any]:
        descriptor_by_step_kind = {desc.step_kind: desc for desc in snapshot.capabilities}
        availability_by_step_kind = {item.step_kind: item for item in snapshot.availability}
        descriptor_by_capability_id = {desc.capability_id: desc for desc in snapshot.capabilities}
        availability_by_capability_id = {item.capability_id: item for item in snapshot.availability}
        return {
            "descriptor_by_step_kind": descriptor_by_step_kind,
            "availability_by_step_kind": availability_by_step_kind,
            "descriptor_by_capability_id": descriptor_by_capability_id,
            "availability_by_capability_id": availability_by_capability_id,
            "enabled_step_kinds": set(snapshot.available_step_kinds),
        }

    def _validate_step_against_capability_snapshot(self, step: PlanStep, idx: int, snapshot_index: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        loc = f"steps[{idx}]"
        descriptor = snapshot_index["descriptor_by_step_kind"].get(step.kind)
        availability = snapshot_index["availability_by_step_kind"].get(step.kind)
        enabled_step_kinds = snapshot_index["enabled_step_kinds"]

        if step.kind in enabled_step_kinds and descriptor is None:
            issues.append(self._issue("CAPABILITY_DESCRIPTOR_MISSING", ValidationSeverity.ERROR, f"enabled step kind {step.kind} has no capability descriptor", loc, step=step))
            return issues

        if descriptor is None or availability is None:
            issues.append(self._issue("CAPABILITY_DESCRIPTOR_MISSING", ValidationSeverity.ERROR, f"step kind {step.kind} is not present in capability snapshot", loc, step=step))
            return issues

        if step.kind not in enabled_step_kinds or availability.status != CapabilityStatus.ENABLED:
            issues.append(self._issue_for_unavailable_capability(step, loc, availability))
            return issues

        errors = validate_payload_against_schema(step.inputs, descriptor.input_schema)
        for error in errors:
            issues.append(
                self._issue(
                    "STEP_INPUT_SCHEMA_INVALID",
                    ValidationSeverity.ERROR,
                    error,
                    loc,
                    step=step,
                    path=self._schema_error_path(loc, error),
                    metadata={"capability_id": descriptor.capability_id},
                )
            )
            issues.append(self._issue("step.inputs.schema_invalid", ValidationSeverity.ERROR, error, loc, step=step))

        issues.extend(self._validate_required_capabilities(step, loc, descriptor, snapshot_index))
        return issues

    def _validate_step_against_registry(self, step: PlanStep, idx: int) -> list[ValidationIssue]:
        loc = f"steps[{idx}]"
        descriptor = self.capability_registry.maybe_get_by_step_kind(step.kind) if self.capability_registry else None
        if descriptor is None:
            return [self._issue("step.capability.unknown", ValidationSeverity.ERROR, f"step kind {step.kind} is not registered as a capability", loc, step=step)]
        issues = []
        for error in validate_payload_against_schema(step.inputs, descriptor.input_schema):
            issues.append(self._issue("STEP_INPUT_SCHEMA_INVALID", ValidationSeverity.ERROR, error, loc, step=step, path=self._schema_error_path(loc, error)))
            issues.append(self._issue("step.inputs.schema_invalid", ValidationSeverity.ERROR, error, loc, step=step))
        return issues

    def _validate_required_capabilities(self, step: PlanStep, loc: str, descriptor: Any, snapshot_index: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if not step.required_capabilities:
            severity = ValidationSeverity.ERROR if self.strict_required_capabilities else ValidationSeverity.WARNING
            issues.append(
                self._issue(
                    "CAPABILITY_REQUIRED_MISSING",
                    severity,
                    f"step {step.step_id} does not declare required_capabilities",
                    loc,
                    step=step,
                    path=f"{loc}.required_capabilities",
                    metadata={"expected_capability_id": descriptor.capability_id},
                )
            )
            return issues

        descriptor_by_capability_id = snapshot_index["descriptor_by_capability_id"]
        availability_by_capability_id = snapshot_index["availability_by_capability_id"]
        for capability_id in step.required_capabilities:
            declared_descriptor = descriptor_by_capability_id.get(capability_id)
            declared_availability = availability_by_capability_id.get(capability_id)
            if declared_descriptor is None or declared_availability is None:
                issues.append(
                    self._issue(
                        "CAPABILITY_REQUIRED_UNKNOWN",
                        ValidationSeverity.ERROR,
                        f"required capability {capability_id} is not present in capability snapshot",
                        loc,
                        step=step,
                        path=f"{loc}.required_capabilities",
                        metadata={"capability_id": capability_id},
                    )
                )
                continue
            if declared_availability.status != CapabilityStatus.ENABLED:
                issues.append(
                    self._issue(
                        "CAPABILITY_REQUIRED_UNAVAILABLE",
                        ValidationSeverity.ERROR,
                        f"required capability {capability_id} is {declared_availability.status}",
                        loc,
                        step=step,
                        path=f"{loc}.required_capabilities",
                        metadata={"capability_id": capability_id, "status": declared_availability.status},
                    )
                )

        if descriptor.capability_id not in step.required_capabilities:
            severity = ValidationSeverity.ERROR if self.strict_required_capabilities else ValidationSeverity.WARNING
            issues.append(
                self._issue(
                    "CAPABILITY_REQUIRED_MISMATCH",
                    severity,
                    f"required_capabilities does not include capability for step kind {step.kind}",
                    loc,
                    step=step,
                    path=f"{loc}.required_capabilities",
                    metadata={"expected_capability_id": descriptor.capability_id, "declared_capability_ids": list(step.required_capabilities)},
                )
            )
        return issues

    def _issue_for_unavailable_capability(self, step: PlanStep, loc: str, availability: Any) -> ValidationIssue:
        status = availability.status
        severity = ValidationSeverity.ERROR
        code = "CAPABILITY_STEP_KIND_UNAVAILABLE"
        if status == CapabilityStatus.PLACEHOLDER:
            code = "CAPABILITY_PLACEHOLDER_USED"
        elif status == CapabilityStatus.DISABLED:
            code = "CAPABILITY_DISABLED_USED"
        elif status == CapabilityStatus.DEPRECATED:
            code = "CAPABILITY_DEPRECATED_USED"
            if self.allow_deprecated_capability:
                severity = ValidationSeverity.WARNING
        elif status == CapabilityStatus.UNAVAILABLE:
            code = "CAPABILITY_STEP_KIND_UNAVAILABLE"
        return self._issue(
            code,
            severity,
            f"capability for step kind {step.kind} is {status}: {availability.reason or 'not enabled'}",
            loc,
            step=step,
            path=f"{loc}.kind",
            metadata={"capability_id": availability.capability_id, "status": status, "missing_context_keys": availability.missing_context_keys},
        )

    @staticmethod
    def _schema_error_path(loc: str, error: str) -> str:
        if error.startswith("$."):
            path = error.split(":", 1)[0].replace("$", f"{loc}.inputs", 1)
            return path
        if error.startswith("$"):
            return error.split(":", 1)[0].replace("$", f"{loc}.inputs", 1)
        return f"{loc}.inputs"

    @staticmethod
    def _issue(
        code: str,
        severity: str,
        message: str,
        location: str | None = None,
        *,
        step: PlanStep | None = None,
        path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ValidationIssue:
        return ValidationIssue(
            code=code,
            severity=severity,
            message=message,
            location=location,
            metadata=metadata or {},
            step_id=step.step_id if step is not None else None,
            step_kind=step.kind if step is not None else None,
            path=path or location,
        )

    def _result(self, issues: list[ValidationIssue], *, capability_snapshot: CapabilitySnapshot | None = None) -> PlanValidationResult:
        has_error = any(i.severity == ValidationSeverity.ERROR for i in issues)
        has_warning = any(i.severity == ValidationSeverity.WARNING for i in issues)
        failed = has_error or (self.fail_on_warning and has_warning)
        metadata: dict[str, Any] = {}
        if capability_snapshot is not None:
            metadata = {
                "capability_snapshot_id": capability_snapshot.snapshot_id,
                "capability_digest": capability_snapshot.capability_digest,
            }
        return PlanValidationResult(
            status=ValidationStatus.FAILED if failed else ValidationStatus.PASSED,
            issues=issues,
            checked_at=int(time.time()),
            metadata=metadata,
        )
