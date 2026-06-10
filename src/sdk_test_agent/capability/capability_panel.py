from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from .capability_enums import RISK_ORDER, CapabilityStatus
from .capability_models import BuildCapabilitySnapshotInput, CapabilityAvailability, CapabilityDescriptor, CapabilitySnapshot
from .capability_registry import CapabilityRegistry
from .trace_models import CapabilityResolutionRecord


def stable_json_dumps(data: object) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256_digest(data: object) -> str:
    payload = stable_json_dumps(data).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class CapabilityPanel:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def build_snapshot(self, request: BuildCapabilitySnapshotInput) -> CapabilitySnapshot:
        descriptors = self.registry.list_all()
        availability = tuple(self._resolve_descriptor(descriptor, request) for descriptor in descriptors)
        available_step_kinds = tuple(a.step_kind for a in availability if a.status == CapabilityStatus.ENABLED)
        unavailable_step_kinds = tuple(a.step_kind for a in availability if a.status != CapabilityStatus.ENABLED)
        snapshot_without_digest = {
            "capabilities": [self._descriptor_digest_payload(d) for d in descriptors],
            "availability": [self._availability_digest_payload(a) for a in availability],
            "available_step_kinds": available_step_kinds,
            "unavailable_step_kinds": unavailable_step_kinds,
        }
        digest = sha256_digest(snapshot_without_digest)
        return CapabilitySnapshot(
            snapshot_id=self._new_id("capsnap"),
            task_id=request.task_id,
            capabilities=descriptors,
            availability=availability,
            available_step_kinds=available_step_kinds,
            unavailable_step_kinds=unavailable_step_kinds,
            capability_digest=digest,
            metadata={
                "task_type": request.task_type,
                "required_capability_ids": list(request.required_capability_ids),
                "recommended_capability_ids": list(request.recommended_capability_ids),
                "max_risk_level": request.max_risk_level,
            },
        )

    def build_resolution_record(
        self,
        request: BuildCapabilitySnapshotInput,
        snapshot: CapabilitySnapshot,
        *,
        prompt_artifact_id: str | None = None,
        snapshot_artifact_id: str | None = None,
        created_at: float | None = None,
    ) -> CapabilityResolutionRecord:
        by_status = {status.value: [] for status in CapabilityStatus}
        for availability in snapshot.availability:
            by_status[availability.status.value].append(availability.capability_id)
        return CapabilityResolutionRecord(
            record_id=self._new_id("capres"),
            task_id=request.task_id,
            input_payload=request.model_dump(mode="json"),
            output_snapshot_id=snapshot.snapshot_id,
            output_capability_digest=snapshot.capability_digest,
            descriptor_ids=[d.capability_id for d in snapshot.capabilities],
            enabled_capability_ids=by_status[CapabilityStatus.ENABLED.value],
            disabled_capability_ids=by_status[CapabilityStatus.DISABLED.value],
            unavailable_capability_ids=by_status[CapabilityStatus.UNAVAILABLE.value],
            placeholder_capability_ids=by_status[CapabilityStatus.PLACEHOLDER.value],
            deprecated_capability_ids=by_status[CapabilityStatus.DEPRECATED.value],
            availability_records=[a.model_dump(mode="json") for a in snapshot.availability],
            prompt_artifact_id=prompt_artifact_id,
            snapshot_artifact_id=snapshot_artifact_id,
            created_at=created_at if created_at is not None else time.time(),
        )

    def build_snapshot_and_record(self, request: BuildCapabilitySnapshotInput) -> tuple[CapabilitySnapshot, CapabilityResolutionRecord]:
        snapshot = self.build_snapshot(request)
        return snapshot, self.build_resolution_record(request, snapshot)

    def _resolve_descriptor(self, descriptor: CapabilityDescriptor, request: BuildCapabilitySnapshotInput) -> CapabilityAvailability:
        available_context = set(request.available_context_keys)
        missing_context = tuple(k for k in descriptor.required_context_keys if k not in available_context)

        if descriptor.is_placeholder and not request.allow_placeholder:
            return self._availability(descriptor, CapabilityStatus.PLACEHOLDER, "placeholder capability is disabled by default")
        if descriptor.is_deprecated and not request.allow_deprecated:
            return self._availability(descriptor, CapabilityStatus.DEPRECATED, "deprecated capability is not allowed")
        if not descriptor.default_enabled:
            return self._availability(descriptor, CapabilityStatus.DISABLED, "capability is disabled by default")
        if descriptor.capability_id in request.forbidden_capability_ids:
            return self._availability(descriptor, CapabilityStatus.DISABLED, "capability is forbidden by skill or policy", blocked_by_skill=True)
        flag_name = f"capability.{descriptor.capability_id}.enabled"
        if flag_name in request.feature_flags and not request.feature_flags[flag_name]:
            return self._availability(descriptor, CapabilityStatus.DISABLED, "capability is disabled by feature flag", blocked_by_feature_flag=True)
        if missing_context:
            return self._availability(descriptor, CapabilityStatus.UNAVAILABLE, "required execution context is unavailable", missing_context_keys=missing_context)
        if RISK_ORDER[str(descriptor.risk_level.value if hasattr(descriptor.risk_level, "value") else descriptor.risk_level)] > RISK_ORDER[str(request.max_risk_level.value if hasattr(request.max_risk_level, "value") else request.max_risk_level)]:
            return self._availability(descriptor, CapabilityStatus.DISABLED, "capability risk exceeds task policy", blocked_by_policy=True)
        return self._availability(descriptor, CapabilityStatus.ENABLED, None)

    @staticmethod
    def _availability(
        descriptor: CapabilityDescriptor,
        status: CapabilityStatus,
        reason: str | None,
        *,
        missing_context_keys: tuple[str, ...] = (),
        blocked_by_policy: bool = False,
        blocked_by_skill: bool = False,
        blocked_by_feature_flag: bool = False,
    ) -> CapabilityAvailability:
        return CapabilityAvailability(
            capability_id=descriptor.capability_id,
            step_kind=descriptor.step_kind,
            status=status,
            reason=reason,
            missing_context_keys=missing_context_keys,
            blocked_by_policy=blocked_by_policy,
            blocked_by_skill=blocked_by_skill,
            blocked_by_feature_flag=blocked_by_feature_flag,
            effective_risk_level=descriptor.risk_level,
        )

    @staticmethod
    def digest_payload(snapshot: CapabilitySnapshot) -> dict[str, Any]:
        return {
            "capabilities": [CapabilityPanel._descriptor_digest_payload(d) for d in snapshot.capabilities],
            "availability": [CapabilityPanel._availability_digest_payload(a) for a in snapshot.availability],
            "available_step_kinds": snapshot.available_step_kinds,
            "unavailable_step_kinds": snapshot.unavailable_step_kinds,
        }

    @staticmethod
    def recompute_digest(snapshot: CapabilitySnapshot) -> str:
        return sha256_digest(CapabilityPanel.digest_payload(snapshot))

    @staticmethod
    def _descriptor_digest_payload(descriptor: CapabilityDescriptor) -> dict[str, Any]:
        return {
            "capability_id": descriptor.capability_id,
            "version": descriptor.version,
            "step_kind": descriptor.step_kind,
            "input_schema": descriptor.input_schema,
            "output_schema": descriptor.output_schema,
            "required_context_keys": descriptor.required_context_keys,
            "risk_level": descriptor.risk_level,
            "visibility": descriptor.visibility,
            "default_enabled": descriptor.default_enabled,
            "is_placeholder": descriptor.is_placeholder,
            "is_deprecated": descriptor.is_deprecated,
        }

    @staticmethod
    def _availability_digest_payload(availability: CapabilityAvailability) -> dict[str, Any]:
        return {
            "capability_id": availability.capability_id,
            "step_kind": availability.step_kind,
            "status": availability.status,
            "reason": availability.reason,
            "missing_context_keys": availability.missing_context_keys,
        }

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:26]}"
