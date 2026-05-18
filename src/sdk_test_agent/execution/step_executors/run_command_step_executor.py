from __future__ import annotations

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep


class RunCommandStepExecutor:
    step_kind = PlanStepKind.RUN_COMMAND

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.command_controller is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="command_controller is not configured")
        action = step.inputs.get("action", "inspect_exec")
        payload = dict(step.inputs.get("payload", {}))
        if "cmd" in payload and "argv" not in payload:
            payload["argv"] = payload.pop("cmd")
        response = context.command_controller.execute_action(action, payload)
        data = response.get("data", {})
        exit_code = data.get("exit_code")
        status = ExecutionStepStatus.SUCCEEDED if response.get("ok") and (exit_code in (None, 0)) else ExecutionStepStatus.FAILED
        return StepExecutionResult(
            status=status,
            outputs={"action": action, "response": response, "exit_code": exit_code},
            stdout=data.get("stdout"),
            stderr=data.get("stderr"),
            error_type=None if status == ExecutionStepStatus.SUCCEEDED else "CommandFailed",
            error_message=None if status == ExecutionStepStatus.SUCCEEDED else response.get("error") or f"command action {action} failed",
        )
