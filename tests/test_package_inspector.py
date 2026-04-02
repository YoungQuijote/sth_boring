import io
import zipfile

from sdk_test_agent.inspection.inspection_enums import InspectionStatus
from sdk_test_agent.inspection.package_inspector.java_package_inspector import JavaPackageInspector
from sdk_test_agent.inspection.package_inspector.package_inspector_models import JavaPackageInspectionInput


def _jar_with_manifest(main_class: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        manifest = "Manifest-Version: 1.0\n"
        if main_class:
            manifest += f"Main-Class: {main_class}\n"
        zf.writestr("META-INF/MANIFEST.MF", manifest)
    return buf.getvalue()


def test_java_package_inspector_jar_only_partial() -> None:
    ins = JavaPackageInspector()
    report = ins.inspect_java_package(
        JavaPackageInspectionInput(
            sdk_name="demo",
            sdk_version="1.0",
            jar_bytes=_jar_with_manifest(),
            pom_xml_bytes=None,
        )
    )
    assert report.status in (InspectionStatus.PARTIAL, InspectionStatus.SUCCESS)
    assert report.language == "java"


def test_java_package_inspector_extracts_pom_and_manifest() -> None:
    ins = JavaPackageInspector()
    pom = b"""<project><artifactId>a</artifactId><version>1.2.3</version><properties><java.version>17</java.version></properties></project>"""
    report = ins.inspect_java_package(
        JavaPackageInspectionInput(
            sdk_name="demo",
            sdk_version=None,
            jar_bytes=_jar_with_manifest("com.demo.Main"),
            pom_xml_bytes=pom,
        )
    )
    assert report.package_name == "a"
    assert report.version == "1.2.3"
    assert report.runtime_hints.main_class == "com.demo.Main"
    assert report.runtime_hints.java_version == "17"


def test_java_package_inspector_embedded_jdk() -> None:
    ins = JavaPackageInspector()
    report = ins.inspect_java_package(
        JavaPackageInspectionInput(
            sdk_name="demo",
            sdk_version="1.0",
            jar_bytes=_jar_with_manifest(),
            pom_xml_bytes=b"<project></project>",
            jdk_bytes=b"fake-jdk",
        )
    )
    assert report.runtime_hints.use_embedded_jdk is True


def test_java_package_inspector_empty_jar_failed() -> None:
    ins = JavaPackageInspector()
    report = ins.inspect_java_package(
        JavaPackageInspectionInput(
            sdk_name="demo",
            sdk_version="1.0",
            jar_bytes=b"",
            pom_xml_bytes=b"<project></project>",
        )
    )
    assert report.status == InspectionStatus.FAILED
