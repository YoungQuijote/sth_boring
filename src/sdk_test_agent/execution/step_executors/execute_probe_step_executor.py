from __future__ import annotations

import shlex

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep

from ._utils import persist_json


class ExecuteProbeStepExecutor:
    step_kind = PlanStepKind.EXECUTE_PROBE

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.command_controller is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="command_controller is not configured")
        probes = step.inputs.get("probes") or [step.inputs.get("probe")]
        results = []
        stdout_parts = []
        stderr_parts = []
        for probe in [p for p in probes if p]:
            argv = shlex.split(probe) if isinstance(probe, str) else list(probe)
            response = context.command_controller.execute_action("inspect_exec", {"argv": argv, "timeout_sec": step.timeout_sec})
            data = response.get("data", {})
            results.append({"argv": argv, "response": response})
            if data.get("stdout"):
                stdout_parts.append(data["stdout"])
            if data.get("stderr"):
                stderr_parts.append(data["stderr"])
        failed = [r for r in results if not r["response"].get("ok") or r["response"].get("data", {}).get("exit_code") not in (None, 0)]
        status = ExecutionStepStatus.FAILED if failed else ExecutionStepStatus.SUCCEEDED
        refs = []
        ref = persist_json(context, kind="probe.result", name=f"{step.step_id}.probe_result.json", payload=results)
        if ref:
            refs.append(ref)
        return StepExecutionResult(
            status=status,
            outputs={"probe_result": results, "failed_count": len(failed)},
            artifact_refs=refs,
            stdout="\n".join(stdout_parts) or None,
            stderr="\n".join(stderr_parts) or None,
            error_type="ProbeFailed" if failed else None,
            error_message=f"{len(failed)} probe(s) failed" if failed else None,
        )
