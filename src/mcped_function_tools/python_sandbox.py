from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SandboxLimits:
    """Runtime limits for sandboxed Python execution."""

    timeout_seconds: float = 2.0
    memory_mb: int = 256
    max_output_chars: int = 8000


@dataclass(slots=True)
class SandboxResult:
    """Result object returned from the Python sandbox."""

    ok: bool
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


class PythonSandbox:
    """Execute Python code in an isolated subprocess with basic limits.

    Notes:
    - This is a pragmatic local sandbox for agent tool execution.
    - It is *not* a strong security boundary against malicious code.
    """

    def __init__(self, *, python_bin: str | None = None, limits: SandboxLimits | None = None) -> None:
        self.python_bin = python_bin or sys.executable
        self.limits = limits or SandboxLimits()

    def run(self, code: str, *, input_data: dict[str, Any] | None = None) -> SandboxResult:
        with tempfile.TemporaryDirectory(prefix="py_sandbox_") as tmpdir:
            workdir = Path(tmpdir)
            script = workdir / "main.py"

            prelude = textwrap.dedent(
                """
                import json
                import os

                INPUT = json.loads(os.environ.get("PY_SANDBOX_INPUT", "null"))
                """
            )
            script.write_text(f"{prelude}\n{code}\n", encoding="utf-8")

            env = {
                "PYTHONUNBUFFERED": "1",
                "PY_SANDBOX_INPUT": json.dumps(input_data if input_data is not None else None),
            }

            try:
                completed = subprocess.run(
                    [self.python_bin, "-I", "-B", str(script)],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    timeout=self.limits.timeout_seconds,
                    env=env,
                    preexec_fn=self._build_preexec_fn(self.limits.memory_mb),
                )
            except subprocess.TimeoutExpired as exc:
                return SandboxResult(
                    ok=False,
                    exit_code=None,
                    stdout=self._trim((exc.stdout or ""), self.limits.max_output_chars),
                    stderr=self._trim((exc.stderr or ""), self.limits.max_output_chars),
                    timed_out=True,
                )

            stdout = self._trim(completed.stdout, self.limits.max_output_chars)
            stderr = self._trim(completed.stderr, self.limits.max_output_chars)
            return SandboxResult(
                ok=completed.returncode == 0,
                exit_code=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
            )

    @staticmethod
    def _trim(value: str, max_chars: int) -> str:
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + "\n...<truncated>"

    @staticmethod
    def _build_preexec_fn(memory_mb: int):
        def _limit_resources() -> None:
            try:
                import resource

                mem_bytes = memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            except Exception:
                # If resource limits are not supported in the environment,
                # continue without hard memory limits.
                return

        return _limit_resources
