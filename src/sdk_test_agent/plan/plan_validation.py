from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sdk_test_agent.capability.capability_enums import CapabilityStatus
from sdk_test_agent.capability.capability_models import CapabilitySnapshot
from sdk_test_agent.capability.capability_registry import CapabilityRegistry
from sdk_test_agent.capability.schema_validation import validate_payload_against_schema

from .plan_enums import VALID_FAILURE_POLICIES, VALID_RISK_LEVELS, StepRiskLevel, ValidationSeverity, ValidationStatus
from .plan_models import ExecutionPlan, ExecutionPlanDraft, PlanStep


@dataclass(slots=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlanValidationResult:
    status: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED


class PlanValidator:
    def __init__(
        self,
        supported_step_kinds: set[str],
        available_capabilities: set[str] | None = None,
        max_step_count: int | None = None,
        capability_registry: CapabilityRegistry | None = None,
    ) -> None:
        self.supported_step_kinds = supported_step_kinds
        self.available_capabilities = available_capabilities
        self.max_step_count = max_step_count
        self.capability_registry = capability_registry

    def validate(self, plan: ExecutionPlan | ExecutionPlanDraft, capability_snapshot: CapabilitySnapshot | None = None) -> PlanValidationResult:
        issues: list[ValidationIssue] = []
        steps = list(plan.steps or [])
        if not steps:
            issues.append(self._issue("plan.steps.empty", ValidationSeverity.ERROR, "plan must contain at least one step"))
            return self._result(issues)

        if self.max_step_count is not None and len(steps) > self.max_step_count:
            issues.append(
                self._issue(
                    "plan.steps.too_many",
                    ValidationSeverity.ERROR,
                    f"plan has {len(steps)} steps, max is {self.max_step_count}",
                )
            )

        seen: set[str] = set()
        for idx, step in enumerate(steps):
            loc = f"steps[{idx}]"
            if not step.step_id:
                issues.append(self._issue("step.id.empty", ValidationSeverity.ERROR, "step_id is required", loc))
            if step.step_id in seen:
                issues.append(self._issue("step.id.duplicate", ValidationSeverity.ERROR, f"duplicate step_id {step.step_id}", loc))
            seen.add(step.step_id)

        known = {s.step_id for s in steps}
        for idx, step in enumerate(steps):
            issues.extend(self._validate_step(step, idx, known, capability_snapshot))

        return self._result(issues)

    def _validate_step(self, step: PlanStep, idx: int, known_step_ids: set[str], capability_snapshot: CapabilitySnapshot | None = None) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        loc = f"steps[{idx}]"
        for dep in step.depends_on:
            if dep not in known_step_ids:
                issues.append(self._issue("step.depends_on.missing", ValidationSeverity.ERROR, f"unknown dependency {dep}", loc))
        if step.kind not in self.supported_step_kinds:
            issues.append(self._issue("step.kind.unsupported", ValidationSeverity.ERROR, f"unsupported step kind {step.kind}", loc))
        if self.available_capabilities is not None:
            for cap in step.required_capabilities:
                if cap not in self.available_capabilities:
                    issues.append(self._issue("step.capability.missing", ValidationSeverity.ERROR, f"missing capability {cap}", loc))
        if step.risk_level not in VALID_RISK_LEVELS:
            issues.append(self._issue("step.risk.invalid", ValidationSeverity.ERROR, f"invalid risk_level {step.risk_level}", loc))
        if step.risk_level == StepRiskLevel.HIGH:
            issues.append(self._issue("step.risk.high", ValidationSeverity.WARNING, "high risk step requires review", loc))
        if step.on_failure not in VALID_FAILURE_POLICIES:
            issues.append(self._issue("step.on_failure.invalid", ValidationSeverity.ERROR, f"invalid on_failure {step.on_failure}", loc))
        issues.extend(self._validate_step_capability_contract(step, loc, capability_snapshot))
        return issues

    def _validate_step_capability_contract(self, step: PlanStep, loc: str, capability_snapshot: CapabilitySnapshot | None) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        descriptor = None
        availability = None
        if capability_snapshot is not None:
            descriptor_by_kind = {d.step_kind: d for d in capability_snapshot.capabilities}
            availability_by_kind = {a.step_kind: a for a in capability_snapshot.availability}
            descriptor = descriptor_by_kind.get(step.kind)
            availability = availability_by_kind.get(step.kind)
            if descriptor is None or availability is None:
                issues.append(self._issue("step.capability.unknown", ValidationSeverity.ERROR, f"step kind {step.kind} is not present in capability snapshot", loc))
                return issues
            if availability.status != CapabilityStatus.ENABLED:
                issues.append(
                    self._issue(
                        "step.capability.unavailable",
                        ValidationSeverity.ERROR,
                        f"capability for step kind {step.kind} is {availability.status}: {availability.reason or 'not enabled'}",
                        loc,
                    )
                )
        elif self.capability_registry is not None:
            descriptor = self.capability_registry.maybe_get_by_step_kind(step.kind)
            if descriptor is None:
                issues.append(self._issue("step.capability.unknown", ValidationSeverity.ERROR, f"step kind {step.kind} is not registered as a capability", loc))
                return issues

        if descriptor is not None:
            errors = validate_payload_against_schema(step.inputs, descriptor.input_schema)
            for error in errors:
                issues.append(self._issue("step.inputs.schema_invalid", ValidationSeverity.ERROR, error, loc))
        return issues

    @staticmethod
    def _issue(code: str, severity: str, message: str, location: str | None = None) -> ValidationIssue:
        return ValidationIssue(code=code, severity=severity, message=message, location=location)

    @staticmethod
    def _result(issues: list[ValidationIssue]) -> PlanValidationResult:
        failed = any(i.severity == ValidationSeverity.ERROR for i in issues)
        return PlanValidationResult(status=ValidationStatus.FAILED if failed else ValidationStatus.PASSED, issues=issues)
