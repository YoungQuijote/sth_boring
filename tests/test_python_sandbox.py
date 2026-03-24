from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.models import BuildImageResult, BuildImageSpec, ContainerCreateSpec, ContainerRef, ExecCreateSpec
from sdk_test_agent.sandbox.models import ExecResult, SandboxSpec
from sdk_test_agent.sandbox.python.docker_sandbox import DockerPythonSandbox


class FakeDriver(BaseDockerDriver):
    def __init__(self):
        self.created = False

    def connect(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def ensure_image(self, image: str, pull_policy: str = "if_missing") -> str:
        return "img-123"

    def build_image(self, spec: BuildImageSpec) -> BuildImageResult:
        return BuildImageResult(image_id="img-123", tags=["test:latest"], logs=[])

    def create_container(self, spec: ContainerCreateSpec) -> ContainerRef:
        self.created = True
        return ContainerRef(container_id="c-1", name="sandbox", status="created")

    def start_container(self, container_id: str) -> None:
        return None

    def exec(self, spec: ExecCreateSpec, timeout_sec: int | None = None) -> ExecResult:
        return ExecResult(exit_code=0, stdout=(" ".join(spec.argv)).encode(), stderr=b"", duration_sec=0.01, meta={})

    def put_archive(self, container_id: str, dest: str, data: bytes) -> None:
        return None

    def get_archive(self, container_id: str, path: str) -> tuple[bytes, dict]:
        return b"tgz", {"path": path}

    def logs(self, container_id: str, tail: int | str = 200) -> bytes:
        return b"logs"

    def inspect_container(self, container_id: str) -> ContainerRef:
        return ContainerRef(container_id=container_id, name="sandbox", status="running", attrs={})

    def stop_container(self, container_id: str, timeout_sec: int = 10) -> None:
        return None

    def remove_container(self, container_id: str, force: bool = False, remove_volumes: bool = False) -> None:
        return None


def test_docker_python_sandbox_lifecycle_and_commands() -> None:
    sandbox = DockerPythonSandbox(SandboxSpec(sandbox_id="s1"), FakeDriver())
    sandbox.create()
    sandbox.prepare_image()
    sandbox.start()

    py = sandbox.run_python(["-V"])
    assert py.exit_code == 0
    assert b"python -V" in py.stdout

    pip = sandbox.run_pip(["install", "-e", "."])
    assert pip.exit_code == 0

    pt = sandbox.run_pytest(["tests/test_smoke.py"], ["-q"])
    assert pt.exit_code == 0

    data, _ = sandbox.get_archive("out")
    assert data == b"tgz"

    sandbox.destroy()
    sandbox.destroy()  # idempotent
