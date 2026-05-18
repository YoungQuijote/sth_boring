from __future__ import annotations

from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlanStepKind


class GenerateScriptStepExecutor:
    step_kind = PlanStepKind.GENERATE_SCRIPT

    def execute(self, step, context) -> StepExecutionResult:
        return StepExecutionResult(
            status=ExecutionStepStatus.SKIPPED,
            error_type="TemporarilyNotImplemented",
            error_message="Temporarily not implemented in v1. Reserved for future script-agent integration.",
        )
