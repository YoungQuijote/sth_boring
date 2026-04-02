from __future__ import annotations

from dataclasses import dataclass, field

from ..inspection_models import InspectionReportBase


@dataclass(slots=True)
class JavaPackageInspectionInput:
    sdk_name: str
    sdk_version: str | None
    jar_bytes: bytes
    pom_xml_bytes: bytes | None
    settings_xml_bytes: bytes | None = None
    jdk_bytes: bytes | None = None


@dataclass(slots=True)
class PackageRuntimeHints:
    base_image: str | None = None
    java_version: str | None = None
    main_class: str | None = None
    packaging: str | None = None
    use_embedded_jdk: bool = False


@dataclass(slots=True)
class PackageInspectionReport(InspectionReportBase):
    language: str | None = None
    package_type: str | None = None
    build_system: str | None = None
    package_name: str | None = None
    version: str | None = None
    dependency_files: list[str] = field(default_factory=list)
    entrypoint_hints: list[str] = field(default_factory=list)
    example_files: list[str] = field(default_factory=list)
    runtime_hints: PackageRuntimeHints = field(default_factory=PackageRuntimeHints)
