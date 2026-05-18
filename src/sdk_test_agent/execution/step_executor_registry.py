from __future__ import annotations

from sdk_test_agent.execution.execution_errors import ExecutionUnsupportedStepKindError
from sdk_test_agent.execution.step_executor_base import BaseStepExecutor


class StepExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[str, BaseStepExecutor] = {}

    def register(self, executor: BaseStepExecutor) -> None:
        self._executors[executor.step_kind] = executor

    def get(self, step_kind: str) -> BaseStepExecutor:
        try:
            return self._executors[step_kind]
        except KeyError as exc:
            raise ExecutionUnsupportedStepKindError(step_kind) from exc

    def supported_step_kinds(self) -> set[str]:
        return set(self._executors)
