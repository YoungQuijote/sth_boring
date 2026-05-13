from pathlib import Path

from sdk_test_agent.artifact_manager import ARTIFACT_DB_NAME, ArtifactManagerRepo, ArtifactManagerService
from sdk_test_agent.control_plane.runtime_manager.runtime_manager_service import RuntimeManagerService
from sdk_test_agent.control_plane.runtime_registry.runtime_registry_enums import RUNTIME_DB_NAME
from sdk_test_agent.control_plane.runtime_registry.runtime_registry_repo import RuntimeRegistryRepo
from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.docker_driver_models import BuildImageResult, BuildImageSpec, ContainerCreateSpec, ContainerRef, ExecCreateSpec
from sdk_test_agent.inspection.env_inspector.docker_env_inspector import DockerEnvInspector
from sdk_test_agent.inspection.package_inspector.java_package_inspector import JavaPackageInspector
from sdk_test_agent.loop import JavaDeployInput, MinimalLoopService
from sdk_test_agent.sandbox.sandbox_models import ExecResult


class FakeDriver(BaseDockerDriver):
    def connect(self):
        return None

    def ping(self):
        return True

    def ensure_image(self, image: str, pull_policy: str = "if_missing") -> str:
        return "img1"

    def build_image(self, spec: BuildImageSpec) -> BuildImageResult:
        return BuildImageResult(image_id="img1", tags=[spec.tag or "demo:latest"], logs=[])

    def create_container(self, spec: ContainerCreateSpec) -> ContainerRef:
        return ContainerRef(container_id="c1", name="demo", status="created")

    def start_container(self, container_id: str):
        return None

    def exec(self, spec: ExecCreateSpec, timeout_sec: int | None = None) -> ExecResult:
        return ExecResult(exit_code=0)

    def put_archive(self, container_id: str, dest: str, data: bytes):
        return None

    def get_archive(self, container_id: str, path: str):
        return b"", {}

    def logs(self, container_id: str, tail: int | str = 200):
        return b""

    def inspect_container(self, container_id: str) -> ContainerRef:
        return ContainerRef(container_id=container_id, name="demo", status="running")

    def stop_container(self, container_id: str, timeout_sec: int = 10):
        return None

    def remove_container(self, container_id: str, force: bool = False, remove_volumes: bool = False):
        return None


def test_minimal_loop_java_deploy(tmp_path: Path) -> None:
    artifact_repo = ArtifactManagerRepo(str(tmp_path / ARTIFACT_DB_NAME))
    artifact_repo.init_schema()
    artifact_svc = ArtifactManagerService(artifact_repo, str(tmp_path / "artifact_root"))

    runtime_repo = RuntimeRegistryRepo(str(tmp_path / RUNTIME_DB_NAME))
    runtime_repo.init_schema()
    runtime_svc = RuntimeManagerService(FakeDriver(), runtime_repo, engine_id="engine_X", now_fn=lambda: "2026-01-01T00:00:00Z")

    loop = MinimalLoopService(artifact_svc, runtime_svc, FakeDriver())
    out = loop.run_java_deploy(
        JavaDeployInput(
            sdk_name="demo-sdk",
            sdk_version="1.0.0",
            jar_bytes=b"jar",
            pom_xml_bytes=b"<project/>",
        )
    )

    assert out.image_id == "img1"
    assert out.container_id == "c1"
    assert out.deployment_id.startswith("deploy_")
    assert len(out.artifact_ids) == 3


def test_minimal_loop_with_inspectors(tmp_path: Path) -> None:
    artifact_repo = ArtifactManagerRepo(str(tmp_path / ARTIFACT_DB_NAME))
    artifact_repo.init_schema()
    artifact_svc = ArtifactManagerService(artifact_repo, str(tmp_path / "artifact_root"))

    runtime_repo = RuntimeRegistryRepo(str(tmp_path / RUNTIME_DB_NAME))
    runtime_repo.init_schema()
    driver = FakeDriver()
    runtime_svc = RuntimeManagerService(driver, runtime_repo, engine_id="engine_X", now_fn=lambda: "2026-01-01T00:00:00Z")

    loop = MinimalLoopService(
        artifact_svc,
        runtime_svc,
        driver,
        package_inspector=JavaPackageInspector(),
        env_inspector=DockerEnvInspector(driver),
    )
    out = loop.run_java_deploy(
        JavaDeployInput(
            sdk_name="demo-sdk",
            sdk_version="1.0.0",
            jar_bytes=b"jar",
            pom_xml_bytes=b"<project/>",
            jdk_bytes=b"jdk",
        )
    )

    assert out.package_inspection_status in ("success", "partial", "failed")
    assert out.env_inspection_status in ("success", "partial", "failed")
