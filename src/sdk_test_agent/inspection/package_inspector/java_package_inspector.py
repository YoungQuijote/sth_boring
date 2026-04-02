from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

from ..inspection_enums import FindingLevel, InspectionStatus, InspectionSubjectType
from ..inspection_models import InspectionEvidence, InspectionFinding
from .package_inspector_base import BasePackageInspector
from .package_inspector_models import JavaPackageInspectionInput, PackageInspectionReport


class JavaPackageInspector(BasePackageInspector):
    inspector_name = "java_package_inspector"

    def inspect_java_package(self, data: JavaPackageInspectionInput) -> PackageInspectionReport:
        report = PackageInspectionReport(
            subject_type=InspectionSubjectType.PACKAGE,
            subject_name=data.sdk_name,
            status=InspectionStatus.SUCCESS,
            language="java",
            package_type="jar_binary",
            build_system="maven" if data.pom_xml_bytes else "unknown",
            package_name=data.sdk_name,
            version=data.sdk_version,
        )
        report.runtime_hints.base_image = "eclipse-temurin:17-jre"
        report.runtime_hints.use_embedded_jdk = data.jdk_bytes is not None

        if not data.jar_bytes:
            report.status = InspectionStatus.FAILED
            report.findings.append(
                InspectionFinding(
                    code="jar.empty",
                    level=FindingLevel.ERROR,
                    summary="jar payload is empty",
                    evidence=[InspectionEvidence(source="input_file", ref="app.jar")],
                )
            )
            return report

        report.dependency_files.append("app.jar")
        if data.pom_xml_bytes:
            report.dependency_files.append("pom.xml")
        else:
            report.status = InspectionStatus.PARTIAL
            report.findings.append(
                InspectionFinding(
                    code="pom.missing",
                    level=FindingLevel.WARNING,
                    summary="pom.xml is missing",
                )
            )

        if data.jdk_bytes is not None:
            report.findings.append(
                InspectionFinding(
                    code="jdk.embedded.present",
                    level=FindingLevel.INFO,
                    summary="embedded jdk archive provided",
                )
            )

        if data.pom_xml_bytes:
            self._inspect_pom(data.pom_xml_bytes, report)

        self._inspect_manifest(data.jar_bytes, report)
        return report

    def _inspect_pom(self, pom_bytes: bytes, report: PackageInspectionReport) -> None:
        try:
            root = ET.fromstring(pom_bytes)
        except Exception:
            report.status = InspectionStatus.PARTIAL
            report.warnings.append("failed to parse pom.xml")
            return

        def find_text(path: str) -> str | None:
            node = root.find(path)
            return node.text.strip() if node is not None and node.text else None

        artifact_id = find_text(".//{*}artifactId")
        version = find_text(".//{*}version")
        packaging = find_text(".//{*}packaging") or "jar"
        java_version = (
            find_text(".//{*}properties/{*}java.version")
            or find_text(".//{*}properties/{*}maven.compiler.source")
            or find_text(".//{*}properties/{*}maven.compiler.target")
        )

        if artifact_id:
            report.package_name = artifact_id
        if version:
            report.version = version
        report.runtime_hints.packaging = packaging

        if java_version:
            report.runtime_hints.java_version = java_version
            report.findings.append(
                InspectionFinding(
                    code="pom.java_version.detected",
                    level=FindingLevel.INFO,
                    summary=f"detected java version {java_version}",
                )
            )

        raw = pom_bytes.decode("utf-8", errors="ignore")
        if "spring-boot-maven-plugin" in raw:
            report.entrypoint_hints.append("spring-boot-maven-plugin")

    def _inspect_manifest(self, jar_bytes: bytes, report: PackageInspectionReport) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(jar_bytes)) as zf:
                if "META-INF/MANIFEST.MF" not in zf.namelist():
                    report.status = InspectionStatus.PARTIAL if report.status != InspectionStatus.FAILED else report.status
                    report.findings.append(
                        InspectionFinding(
                            code="jar.manifest.missing",
                            level=FindingLevel.WARNING,
                            summary="MANIFEST.MF not found",
                        )
                    )
                    return
                text = zf.read("META-INF/MANIFEST.MF").decode("utf-8", errors="ignore")
        except Exception:
            report.status = InspectionStatus.PARTIAL if report.status != InspectionStatus.FAILED else report.status
            report.warnings.append("unable to inspect jar manifest")
            return

        main = self._extract_manifest_field(text, "Main-Class")
        start = self._extract_manifest_field(text, "Start-Class")
        chosen = main or start
        if chosen:
            report.runtime_hints.main_class = chosen
            report.entrypoint_hints.append(chosen)
            report.findings.append(
                InspectionFinding(
                    code="jar.main_class.detected",
                    level=FindingLevel.INFO,
                    summary=f"detected main class {chosen}",
                    evidence=[InspectionEvidence(source="input_file", ref="MANIFEST.MF", snippet=chosen)],
                )
            )

    @staticmethod
    def _extract_manifest_field(text: str, key: str) -> str | None:
        m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
        return m.group(1).strip() if m else None
