from __future__ import annotations

import time
from typing import Any, Callable

from sdk_test_agent.sandbox.models import ExecResult

from .base import BaseDockerDriver
from .errors import (
    DockerArchiveError,
    DockerConnectionError,
    DockerContainerError,
    DockerExecError,
    DockerImageError,
)
from .models import ContainerCreateSpec, ContainerRef, DriverConfig, ExecCreateSpec


class DockerSdkDriver(BaseDockerDriver):
    """The only layer that directly touches Docker SDK for Python."""

    def __init__(self, config: DriverConfig | None = None, client_factory: Callable[..., Any] | None = None) -> None:
        self.config = config or DriverConfig()
        self._client_factory = client_factory
        self._client: Any | None = None

    def connect(self) -> None:
        try:
            if self._client_factory is not None:
                self._client = self._client_factory()
            else:
                import docker

                if self.config.base_url:
                    self._client = docker.DockerClient(
                        base_url=self.config.base_url,
                        timeout=self.config.timeout,
                        version=self.config.version,
                        use_ssh_client=self.config.use_ssh_client,
                    )
                else:
                    self._client = docker.from_env(timeout=self.config.timeout)
            self._client.ping()
        except Exception as exc:  # noqa: BLE001
            raise DockerConnectionError(str(exc)) from exc

    def ping(self) -> bool:
        if self._client is None:
            self.connect()
        assert self._client is not None
        try:
            return bool(self._client.ping())
        except Exception as exc:  # noqa: BLE001
            raise DockerConnectionError(str(exc)) from exc

    def ensure_image(self, image: str, pull_policy: str = "if_missing") -> str:
        c = self._get_client()
        try:
            if pull_policy == "always":
                img = c.images.pull(image)
                return img.id
            if pull_policy == "if_missing":
                try:
                    img = c.images.get(image)
                except Exception:
                    img = c.images.pull(image)
                return img.id
            if pull_policy == "never":
                img = c.images.get(image)
                return img.id
            raise DockerImageError(f"unknown pull_policy: {pull_policy}")
        except DockerImageError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DockerImageError(str(exc)) from exc

    def create_container(self, spec: ContainerCreateSpec) -> ContainerRef:
        c = self._get_client()
        try:
            container = c.containers.create(
                image=spec.image,
                command=spec.command,
                working_dir=spec.working_dir,
                environment=spec.environment,
                detach=spec.detach,
                mem_limit=spec.mem_limit,
                nano_cpus=spec.nano_cpus,
                network_disabled=spec.network_disabled,
                read_only=spec.read_only,
                user=spec.user,
                auto_remove=spec.auto_remove,
                labels=spec.labels,
            )
            return ContainerRef(
                container_id=container.id,
                name=getattr(container, "name", None),
                status=getattr(container, "status", None),
                attrs=getattr(container, "attrs", {}),
            )
        except Exception as exc:  # noqa: BLE001
            raise DockerContainerError(str(exc)) from exc

    def start_container(self, container_id: str) -> None:
        c = self._get_client()
        try:
            c.containers.get(container_id).start()
        except Exception as exc:  # noqa: BLE001
            raise DockerContainerError(str(exc)) from exc

    def exec(self, spec: ExecCreateSpec, timeout_sec: int | None = None) -> ExecResult:
        c = self._get_client()
        start = time.monotonic()
        try:
            container = c.containers.get(spec.container_id)
            out = container.exec_run(
                cmd=spec.argv,
                workdir=spec.workdir,
                environment=spec.environment,
                user=spec.user,
                tty=spec.tty,
                stream=spec.stream,
                demux=spec.demux,
                socket=False,
            )
            duration = time.monotonic() - start

            exit_code = getattr(out, "exit_code", None)
            output = getattr(out, "output", None)
            stdout: bytes | None = None
            stderr: bytes | None = None
            combined: bytes | None = None

            if isinstance(output, tuple):
                stdout, stderr = output
            elif isinstance(output, bytes):
                combined = output

            return ExecResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                combined=combined,
                duration_sec=duration,
                timed_out=False,
                meta={"argv": spec.argv, "timeout_sec": timeout_sec},
            )
        except Exception as exc:  # noqa: BLE001
            raise DockerExecError(str(exc)) from exc

    def put_archive(self, container_id: str, dest: str, data: bytes) -> None:
        c = self._get_client()
        try:
            ok = c.containers.get(container_id).put_archive(dest, data)
            if not ok:
                raise DockerArchiveError("put_archive returned false")
        except DockerArchiveError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DockerArchiveError(str(exc)) from exc

    def get_archive(self, container_id: str, path: str) -> tuple[bytes, dict]:
        c = self._get_client()
        try:
            stream, stat = c.containers.get(container_id).get_archive(path)
            return b"".join(stream), stat
        except Exception as exc:  # noqa: BLE001
            raise DockerArchiveError(str(exc)) from exc

    def logs(self, container_id: str, tail: int | str = 200) -> bytes:
        c = self._get_client()
        try:
            return c.containers.get(container_id).logs(tail=tail)
        except Exception as exc:  # noqa: BLE001
            raise DockerContainerError(str(exc)) from exc

    def inspect_container(self, container_id: str) -> ContainerRef:
        c = self._get_client()
        try:
            container = c.containers.get(container_id)
            container.reload()
            return ContainerRef(
                container_id=container.id,
                name=getattr(container, "name", None),
                status=getattr(container, "status", None),
                attrs=getattr(container, "attrs", {}),
            )
        except Exception as exc:  # noqa: BLE001
            raise DockerContainerError(str(exc)) from exc

    def stop_container(self, container_id: str, timeout_sec: int = 10) -> None:
        c = self._get_client()
        try:
            c.containers.get(container_id).stop(timeout=timeout_sec)
        except Exception as exc:  # noqa: BLE001
            raise DockerContainerError(str(exc)) from exc

    def remove_container(self, container_id: str, force: bool = False, remove_volumes: bool = False) -> None:
        c = self._get_client()
        try:
            c.containers.get(container_id).remove(force=force, v=remove_volumes)
        except Exception as exc:  # noqa: BLE001
            raise DockerContainerError(str(exc)) from exc

    def _get_client(self) -> Any:
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client
