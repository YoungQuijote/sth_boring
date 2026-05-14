from __future__ import annotations

from .capability_models import CapabilityDescriptor


class CapabilityRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, CapabilityDescriptor] = {}
        self._by_step_kind: dict[str, CapabilityDescriptor] = {}

    def register(self, descriptor: CapabilityDescriptor) -> None:
        if descriptor.capability_id in self._by_id:
            raise ValueError(f"duplicated capability_id: {descriptor.capability_id}")
        if descriptor.step_kind in self._by_step_kind:
            raise ValueError(f"duplicated step_kind: {descriptor.step_kind}")
        self._by_id[descriptor.capability_id] = descriptor
        self._by_step_kind[descriptor.step_kind] = descriptor

    def get_by_id(self, capability_id: str) -> CapabilityDescriptor:
        return self._by_id[capability_id]

    def get_by_step_kind(self, step_kind: str) -> CapabilityDescriptor:
        return self._by_step_kind[step_kind]

    def maybe_get_by_step_kind(self, step_kind: str) -> CapabilityDescriptor | None:
        return self._by_step_kind.get(step_kind)

    def list_all(self) -> tuple[CapabilityDescriptor, ...]:
        return tuple(self._by_id.values())

    def available_step_kinds(self) -> tuple[str, ...]:
        return tuple(self._by_step_kind.keys())
