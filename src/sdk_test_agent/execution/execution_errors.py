from __future__ import annotations


class ExecutionError(Exception):
    """Base error for execution module failures."""


class ExecutionUnsupportedStepKindError(ExecutionError):
    def __init__(self, step_kind: str) -> None:
        self.step_kind = step_kind
        super().__init__(f"unsupported execution step kind: {step_kind}")


class ExecutionDependencyError(ExecutionError):
    """Raised when execution dependencies are inconsistent."""
