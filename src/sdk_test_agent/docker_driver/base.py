from __future__ import annotations

from abc import ABC, abstractmethod

from sdk_test_agent.sandbox.sandbox_models import ExecResult

from .docker_driver_models import BuildImageResult, BuildImageSpec, ContainerCreateSpec, ContainerRef, ExecCreateSpec


class BaseDockerDriver(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def ping(self) -> bool: ...

    @abstractmethod
    def ensure_image(self, image: str, pull_policy: str = "if_missing") -> str: ...

    @abstractmethod
    def build_image(self, spec: BuildImageSpec) -> BuildImageResult: ...

    @abstractmethod
    def create_container(self, spec: ContainerCreateSpec) -> ContainerRef: ...

    @abstractmethod
    def start_container(self, container_id: str) -> None: ...

    @abstractmethod
    def exec(self, spec: ExecCreateSpec, timeout_sec: int | None = None) -> ExecResult: ...

    @abstractmethod
    def put_archive(self, container_id: str, dest: str, data: bytes) -> None: ...

    @abstractmethod
    def get_archive(self, container_id: str, path: str) -> tuple[bytes, dict]: ...

    @abstractmethod
    def logs(self, container_id: str, tail: int | str = 200) -> bytes: ...

    @abstractmethod
    def inspect_container(self, container_id: str) -> ContainerRef: ...

    @abstractmethod
    def stop_container(self, container_id: str, timeout_sec: int = 10) -> None: ...

    @abstractmethod
    def remove_container(self, container_id: str, force: bool = False, remove_volumes: bool = False) -> None: ...
