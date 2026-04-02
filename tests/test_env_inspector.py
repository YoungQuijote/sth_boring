from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.docker_driver_models import BuildImageResult, BuildImageSpec, ContainerCreateSpec, ContainerRef, ExecCreateSpec
from sdk_test_agent.inspection.env_inspector.docker_env_inspector import DockerEnvInspector
from sdk_test_agent.inspection.env_inspector.env_inspector_models import DockerEnvInspectionInput
from sdk_test_agent.inspection.inspection_enums import InspectionStatus
from sdk_test_agent.sandbox.sandbox_models import ExecResult


class FakeDriver(BaseDockerDriver):
    def __init__(self, running: bool = True):
        self.running = running

    def connect(self):
        return None

    def ping(self):
        return True

    def ensure_image(self, image: str, pull_policy: str = "if_missing") -> str:
        return "img1"

    def build_image(self, spec: BuildImageSpec) -> BuildImageResult:
        return BuildImageResult(image_id="img1", tags=[], logs=[])

    def create_container(self, spec: ContainerCreateSpec) -> ContainerRef:
        return ContainerRef(container_id="c1", status="running")

    def start_container(self, container_id: str):
        return None

    def exec(self, spec: ExecCreateSpec, timeout_sec: int | None = None) -> ExecResult:
        if spec.argv in (["mvn", "-v"], ["gradle", "-v"]):
            return ExecResult(exit_code=127, stderr=b"not found")
        return ExecResult(exit_code=0, stdout=(" ".join(spec.argv)).encode())

    def put_archive(self, container_id: str, dest: str, data: bytes):
        return None

    def get_archive(self, container_id: str, path: str):
        return b"", {}

    def logs(self, container_id: str, tail: int | str = 200):
        return b""

    def inspect_container(self, container_id: str) -> ContainerRef:
        return ContainerRef(container_id=container_id, status="running" if self.running else "exited", name="demo")

    def stop_container(self, container_id: str, timeout_sec: int = 10):
        return None

    def remove_container(self, container_id: str, force: bool = False, remove_volumes: bool = False):
        return None


def test_env_inspector_running_container_ready_or_partial() -> None:
    ins = DockerEnvInspector(FakeDriver(running=True))
    report = ins.inspect_docker_env(DockerEnvInspectionInput(engine_id="engine1", image_id="img1", container_id="c1"))
    assert report.status in (InspectionStatus.SUCCESS, InspectionStatus.PARTIAL)
    assert report.readiness in ("ready", "degraded")
    assert len(report.probe_records) >= 3


def test_env_inspector_exited_container_failed() -> None:
    ins = DockerEnvInspector(FakeDriver(running=False))
    report = ins.inspect_docker_env(DockerEnvInspectionInput(engine_id="engine1", image_id="img1", container_id="c1"))
    assert report.status == InspectionStatus.FAILED
    assert report.readiness == "failed"
