from __future__ import annotations

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep

from ._utils import persist_json, persist_text


class CollectArtifactStepExecutor:
    step_kind = PlanStepKind.COLLECT_ARTIFACT

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.artifact_manager is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="artifact_manager is not configured")
        refs = []
        for item in step.inputs.get("items", []):
            name = item.get("name", "artifact.txt")
            kind = item.get("kind", "exec.log")
            content = item.get("content", "")
            ref = persist_text(context, kind=kind, name=name, text=content, mime_type=item.get("mime_type", "text/plain"))
            if ref:
                refs.append(ref)
        summary_ref = persist_json(
            context,
            kind="report.json",
            name=f"{step.step_id}.collected_context.json",
            payload={"step_outputs": context.step_outputs, "artifact_refs": context.artifact_refs, "runtime_refs": context.runtime_refs},
        )
        if summary_ref:
            refs.append(summary_ref)
        return StepExecutionResult(status=ExecutionStepStatus.SUCCEEDED, outputs={"artifact_refs": refs}, artifact_refs=refs)
