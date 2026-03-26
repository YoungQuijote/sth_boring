from __future__ import annotations

from posixpath import normpath
from typing import Any, Protocol

from .cmd_ctrl_errors import PolicyViolationError
from .cmd_ctrl_models import GuardDecision


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


class InspectPolicy:
    def __init__(self, allowed_binaries: set[str] | None = None) -> None:
        self.allowed_binaries = allowed_binaries or {
            "pwd",
            "ls",
            "find",
            "cat",
            "tail",
            "head",
            "grep",
            "env",
            "python",
            "pip",
        }
        self._interactive = {"vi", "vim", "nano", "top", "less", "more", "bash", "sh"}
        self._deny_tokens = {"rm", "mv", "chmod", "chown", "-i", "--in-place"}

    def validate_argv(self, argv: list[str]) -> None:
        if not argv:
            raise PolicyViolationError("inspect argv cannot be empty")

        bin_name = argv[0]
        if bin_name in self._interactive:
            raise PolicyViolationError(f"interactive binary not allowed: {bin_name}")
        if bin_name not in self.allowed_binaries:
            raise PolicyViolationError(f"binary not allowed for inspect: {bin_name}")

        joined = " ".join(argv)
        if any(token in argv for token in self._deny_tokens):
            raise PolicyViolationError("mutating or risky token not allowed in inspect command")
        if " rm " in f" {joined} ":
            raise PolicyViolationError("potentially destructive command pattern detected")

        if bin_name == "python":
            if argv in (["python", "-V"], ["python", "--version"], ["python", "-m", "pip", "list"]):
                return
            raise PolicyViolationError(
                "python inspect only allows `python -V`, `python --version`, or `python -m pip list`"
            )

        if bin_name == "pip" and argv != ["pip", "list"]:
            raise PolicyViolationError("pip inspect only allows `pip list`")


class CommandGuard(Protocol):
    def evaluate(self, argv: list[str], payload: dict[str, Any]) -> GuardDecision:
        ...


class DefaultCommandGuard:
    def evaluate(self, argv: list[str], payload: dict[str, Any]) -> GuardDecision:
        return GuardDecision(
            decision="escalate",
            reason="no concrete guard policy configured",
            meta={"argv": argv, "payload_keys": sorted(payload.keys())},
        )
