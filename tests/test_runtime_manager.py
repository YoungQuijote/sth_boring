from pathlib import Path

from sdk_test_agent.control_plane.runtime_manager.runtime_manager_models import EnvFingerprintInput
from sdk_test_agent.control_plane.runtime_manager.runtime_manager_service import RuntimeManagerService
from sdk_test_agent.control_plane.runtime_registry.runtime_registry_enums import RUNTIME_DB_NAME
from sdk_test_agent.control_plane.runtime_registry.runtime_registry_repo import RuntimeRegistryRepo
from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.docker_driver_models import BuildImageResult, BuildImageSpec, ContainerCreateSpec, ContainerRef, ExecCreateSpec
from sdk_test_agent.sandbox.sandbox_models import ExecResult


class FakeDriver(BaseDockerDriver):
    def connect(self):
        return None

    def ping(self):
        return True

    def ensure_image(self, image: str, pull_policy: str = "if_missing") -> str:
        return "img1"

    def build_image(self, spec: BuildImageSpec) -> BuildImageResult:
        return BuildImageResult(image_id="img1", tags=["demo:latest"], logs=[])

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


def test_runtime_manager_register_and_fingerprint(tmp_path: Path) -> None:
    db = tmp_path / RUNTIME_DB_NAME
    repo = RuntimeRegistryRepo(str(db))
    repo.init_schema()

    svc = RuntimeManagerService(FakeDriver(), repo, engine_id="engine_X", now_fn=lambda: "2026-01-01T00:00:00Z")
    svc.register_host("host_X", "local", "127.0.0.1", '{"cpu": 8}')
    svc.register_engine("host_X", "unix:///var/run/docker.sock", "local")

    cont = svc.create_container(ContainerCreateSpec(image="img1", command=["sleep", "infinity"]))
    fp, raw = svc.make_env_fingerprint(
        EnvFingerprintInput(runtime="docker", engine_id="engine_X", image_id="img1", sdk_name="demo", sdk_version="1.0", command=["sleep", "infinity"], env={}, ports=[])
    )
    assert len(fp) == 64
    assert "engine_X" in raw
    assert cont.container_id == "c1"
