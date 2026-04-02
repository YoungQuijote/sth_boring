from __future__ import annotations

from abc import ABC, abstractmethod

from .package_inspector_models import JavaPackageInspectionInput, PackageInspectionReport


class BasePackageInspector(ABC):
    inspector_name: str

    @abstractmethod
    def inspect_java_package(self, data: JavaPackageInspectionInput) -> PackageInspectionReport:
        raise NotImplementedError
