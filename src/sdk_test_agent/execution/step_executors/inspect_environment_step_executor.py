from __future__ import annotations

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.inspection.env_inspector.env_inspector_models import DockerEnvInspectionInput
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep

from ._utils import find_output, jsonable, persist_json


class InspectEnvironmentStepExecutor:
    step_kind = PlanStepKind.INSPECT_ENVIRONMENT

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.env_inspector is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="env_inspector is not configured")
        container_id = step.inputs.get("container_id") or find_output(context, "container_id") or context.runtime_refs.get("latest_container_id")
        if not container_id:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingInput", error_message="container_id is required to inspect environment")
        data = DockerEnvInspectionInput(
            engine_id=step.inputs.get("engine_id") or find_output(context, "engine_id") or context.metadata.get("engine_id", "unknown"),
            image_id=step.inputs.get("image_id") or find_output(context, "image_id"),
            container_id=container_id,
            runtime_name=step.inputs.get("runtime_name", "docker"),
        )
        report = context.env_inspector.inspect_docker_env(data)
        outputs = {"env_report": report, "readiness": getattr(report, "readiness", "unknown")}
        refs = []
        ref = persist_json(context, kind="report.json", name=f"{step.step_id}.env_report.json", payload=report)
        if ref:
            refs.append(ref)
            context.artifact_refs["latest_env_report"] = ref
        return StepExecutionResult(status=ExecutionStepStatus.SUCCEEDED, outputs=jsonable(outputs), artifact_refs=refs)
