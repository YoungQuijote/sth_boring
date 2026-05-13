from __future__ import annotations

from sdk_test_agent.docker_driver.base import BaseDockerDriver
from sdk_test_agent.docker_driver.docker_driver_models import ContainerCreateSpec, ExecCreateSpec
from sdk_test_agent.sandbox.base import BaseSandbox
from sdk_test_agent.sandbox.sandbox_errors import SandboxNotReadyError, SandboxStateError
from sdk_test_agent.sandbox.sandbox_models import ExecResult, ExecSpec, SandboxSnapshot, SandboxSpec
from sdk_test_agent.sandbox.python.artifact_codec import pack_text_file
from sdk_test_agent.sandbox.utils.paths import safe_join


class DockerPythonSandbox(BaseSandbox):
    def __init__(self, spec: SandboxSpec, driver: BaseDockerDriver) -> None:
        self.spec = spec
        self.driver = driver
        self._status = "created"
        self._container_id: str | None = None
        self._image_id: str | None = None

    def create(self) -> SandboxSnapshot:
        self._status = "created"
        return self.snapshot()

    def prepare_image(self) -> str:
        self._image_id = self.driver.ensure_image(self.spec.image, pull_policy=self.spec.pull_policy)
        self._status = "image_ready"
        return self._image_id

    def start(self) -> SandboxSnapshot:
        if self._status not in {"image_ready", "created"}:
            raise SandboxStateError(f"cannot start from status={self._status}")
        if self._status == "created":
            raise SandboxStateError("prepare_image must be called before start")

        ref = self.driver.create_container(
            ContainerCreateSpec(
                image=self.spec.image,
                command=self.spec.keep_alive_cmd,
                working_dir=self.spec.workdir,
                environment=self.spec.env,
                mem_limit=self.spec.mem_limit,
                nano_cpus=self.spec.nano_cpus,
                network_disabled=self.spec.network_disabled,
                read_only=self.spec.read_only_rootfs,
                user=self.spec.user,
                auto_remove=self.spec.auto_remove,
                labels=self.spec.labels,
            )
        )
        self._container_id = ref.container_id
        self.driver.start_container(self._container_id)
        self._status = "container_running"

        self.exec(ExecSpec(argv=["mkdir", "-p", self.spec.workdir]))
        self._status = "workspace_ready"
        self._status = "ready"
        return self.snapshot()

    def put_workspace_bytes(self, data: bytes, dest: str | None = None) -> None:
        self._require_running()
        assert self._container_id is not None
        self.driver.put_archive(self._container_id, dest or self.spec.workdir, data)

    def put_text(self, path: str, content: str) -> None:
        abs_path = safe_join(self.spec.workdir, path)
        tar_data = pack_text_file(abs_path.lstrip("/"), content)
        self.put_workspace_bytes(tar_data, dest="/")

    def exec(self, spec: ExecSpec, timeout_sec: int | None = None) -> ExecResult:
        self._require_running()
        assert self._container_id is not None
        return self.driver.exec(
            ExecCreateSpec(
                container_id=self._container_id,
                argv=spec.argv,
                workdir=spec.workdir or self.spec.workdir,
                environment=spec.env,
                user=spec.user,
                tty=spec.tty,
                stream=spec.stream,
                demux=spec.demux,
            ),
            timeout_sec=timeout_sec,
        )

    def run_python(self, argv: list[str], **kwargs) -> ExecResult:
        return self.exec(ExecSpec(argv=["python", *argv]), **kwargs)

    def run_pip(self, argv: list[str], **kwargs) -> ExecResult:
        return self.exec(ExecSpec(argv=["python", "-m", "pip", *argv]), **kwargs)

    def run_pytest(self, targets: list[str], extra_args: list[str] | None = None, **kwargs) -> ExecResult:
        return self.exec(ExecSpec(argv=["python", "-m", "pytest", *targets, *(extra_args or [])]), **kwargs)

    def get_archive(self, path: str) -> tuple[bytes, dict]:
        self._require_running()
        assert self._container_id is not None
        abs_path = safe_join(self.spec.workdir, path)
        return self.driver.get_archive(self._container_id, abs_path)

    def logs(self, tail: int | str = 200) -> bytes:
        self._require_running()
        assert self._container_id is not None
        return self.driver.logs(self._container_id, tail=tail)

    def snapshot(self) -> SandboxSnapshot:
        attrs = {"image_id": self._image_id}
        if self._container_id:
            try:
                ref = self.driver.inspect_container(self._container_id)
                attrs["container_status"] = ref.status
                attrs["container_name"] = ref.name
                attrs["container_attrs"] = ref.attrs
            except Exception:
                pass
        return SandboxSnapshot(
            sandbox_id=self.spec.sandbox_id,
            status=self._status,  # type: ignore[arg-type]
            image=self.spec.image,
            container_id=self._container_id,
            workdir=self.spec.workdir,
            attrs=attrs,
        )

    def stop(self, timeout_sec: int = 10) -> None:
        if not self._container_id or self._status in {"stopped", "removed"}:
            return
        self.driver.stop_container(self._container_id, timeout_sec=timeout_sec)
        self._status = "stopped"

    def destroy(self, force: bool = False, remove_volumes: bool = False) -> None:
        if not self._container_id:
            self._status = "removed"
            return
        try:
            self.driver.remove_container(self._container_id, force=force, remove_volumes=remove_volumes)
        finally:
            self._status = "removed"

    def _require_running(self) -> None:
        if self._status not in {"container_running", "workspace_ready", "ready"}:
            raise SandboxNotReadyError(f"sandbox not running, status={self._status}")
        if self._container_id is None:
            raise SandboxNotReadyError("missing container_id")
