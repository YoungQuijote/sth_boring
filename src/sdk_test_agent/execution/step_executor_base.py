from __future__ import annotations

from typing import Protocol

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_models import PlanStep


class BaseStepExecutor(Protocol):
    step_kind: str

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        ...
