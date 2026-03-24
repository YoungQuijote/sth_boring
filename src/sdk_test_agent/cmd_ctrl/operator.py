from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sdk_test_agent.sandbox.base import BaseSandbox
from sdk_test_agent.sandbox.models import ExecResult, ExecSpec

from .errors import GuardDeniedError, GuardEscalationRequired
from .policies import CommandGuard, DefaultCommandGuard, InspectPolicy
from sdk_test_agent.sandbox.models import ExecResult


class BaseOperator(ABC):
    @abstractmethod
    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]: ...

    @staticmethod
    def _exec_to_dict(result: ExecResult) -> dict[str, Any]:
        return {
            "exit_code": result.exit_code,
            "stdout": (result.stdout.decode("utf-8", errors="replace") if result.stdout else None),
            "stderr": (result.stderr.decode("utf-8", errors="replace") if result.stderr else None),
            "combined": (result.combined.decode("utf-8", errors="replace") if result.combined else None),
            "duration_sec": result.duration_sec,
            "timed_out": result.timed_out,
            "meta": result.meta,
        }

    @staticmethod
    def _payload_to_exec_spec(payload: dict[str, Any]) -> tuple[ExecSpec, int | None]:
        argv = payload.get("argv", [])
        workdir = payload.get("workdir")
        timeout_sec = payload.get("timeout_sec")
        return ExecSpec(argv=argv, workdir=workdir), timeout_sec


class InstallSdkOperator(BaseOperator):
    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        mode = payload.get("mode", "editable")
        if mode == "editable":
            path = payload.get("path", ".")
            result = sandbox.run_pip(["install", "-e", path])  # type: ignore[attr-defined]
        elif mode == "requirements":
            req = payload.get("path", "requirements.txt")
            result = sandbox.run_pip(["install", "-r", req])  # type: ignore[attr-defined]
        elif mode == "wheel":
            wheel = payload.get("path", "package.whl")
            result = sandbox.run_pip(["install", wheel])  # type: ignore[attr-defined]
        else:
            raise ValueError(f"unsupported install mode: {mode}")
        return self._exec_to_dict(result)


class WriteFileOperator(BaseOperator):
    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        path = payload["path"]
        content = payload["content"]
        sandbox.put_text(path, content)
        return {"path": path, "bytes": len(content.encode("utf-8"))}


class RunPythonOperator(BaseOperator):
    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        argv = payload.get("argv", [])
        result = sandbox.run_python(argv)  # type: ignore[attr-defined]
        return self._exec_to_dict(result)


class RunPytestOperator(BaseOperator):
    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        targets = payload.get("targets", [])
        extra_args = payload.get("extra_args", [])
        result = sandbox.run_pytest(targets, extra_args)  # type: ignore[attr-defined]
        return self._exec_to_dict(result)


class CollectArtifactsOperator(BaseOperator):
    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        path = payload.get("path", ".")
        data, stat = sandbox.get_archive(path)
        return {"path": path, "size": len(data), "stat": stat, "archive": data}


class InspectExecOperator(BaseOperator):
    def __init__(self, inspect_policy: InspectPolicy | None = None) -> None:
        self.inspect_policy = inspect_policy or InspectPolicy()

    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        spec, timeout_sec = self._payload_to_exec_spec(payload)
        self.inspect_policy.validate_argv(spec.argv)
        result = sandbox.exec(spec, timeout_sec=timeout_sec)
        return self._exec_to_dict(result)


class GuardedExecOperator(BaseOperator):
    def __init__(self, guard: CommandGuard | None = None) -> None:
        self.guard = guard or DefaultCommandGuard()

    def run(self, sandbox: BaseSandbox, payload: dict[str, Any]) -> dict[str, Any]:
        spec, timeout_sec = self._payload_to_exec_spec(payload)
        decision = self.guard.evaluate(spec.argv, payload)

        if decision.decision == "deny":
            raise GuardDeniedError(decision.reason or "guard denied execution")

        if decision.decision == "escalate":
            # Hook for future HITL integration in LangGraph flows.
            # Current phase surfaces a dedicated exception for upper orchestration.
            raise GuardEscalationRequired(decision.reason or "guard escalation required")

        result = sandbox.exec(spec, timeout_sec=timeout_sec)
        return self._exec_to_dict(result)
