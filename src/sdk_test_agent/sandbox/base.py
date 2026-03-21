from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ExecResult, ExecSpec, SandboxSnapshot


class BaseSandbox(ABC):
    @abstractmethod
    def create(self) -> SandboxSnapshot: ...

    @abstractmethod
    def prepare_image(self) -> str: ...

    @abstractmethod
    def start(self) -> SandboxSnapshot: ...

    @abstractmethod
    def put_workspace_bytes(self, data: bytes, dest: str | None = None) -> None: ...

    @abstractmethod
    def put_text(self, path: str, content: str) -> None: ...

    @abstractmethod
    def exec(self, spec: ExecSpec, timeout_sec: int | None = None) -> ExecResult: ...

    @abstractmethod
    def get_archive(self, path: str) -> tuple[bytes, dict]: ...

    @abstractmethod
    def logs(self, tail: int | str = 200) -> bytes: ...

    @abstractmethod
    def snapshot(self) -> SandboxSnapshot: ...

    @abstractmethod
    def stop(self, timeout_sec: int = 10) -> None: ...

    @abstractmethod
    def destroy(self, force: bool = False, remove_volumes: bool = False) -> None: ...
