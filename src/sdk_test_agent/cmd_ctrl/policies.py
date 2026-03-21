from __future__ import annotations

from posixpath import normpath

from .errors import PolicyViolationError


class ActionPolicy:
    def __init__(self, allowed_actions: set[str]) -> None:
        self.allowed_actions = allowed_actions

    def validate_action(self, action: str) -> None:
        if action not in self.allowed_actions:
            raise PolicyViolationError(f"action not allowed: {action}")


class PathPolicy:
    def __init__(self, workdir: str = "/workspace") -> None:
        self.workdir = normpath(workdir)

    def validate_relative_path(self, path: str) -> None:
        clean = normpath(path).lstrip("/")
        if clean.startswith(".."):
            raise PolicyViolationError("path escapes workdir")
