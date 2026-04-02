from __future__ import annotations

from .package_inspector_base import BasePackageInspector
from .package_inspector_models import JavaPackageInspectionInput, PackageInspectionReport


class PackageInspectorService:
    def __init__(self, java_inspector: BasePackageInspector) -> None:
        self.java_inspector = java_inspector

    def inspect_java_package(self, data: JavaPackageInspectionInput) -> PackageInspectionReport:
        return self.java_inspector.inspect_java_package(data)
