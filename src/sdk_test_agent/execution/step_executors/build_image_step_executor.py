from __future__ import annotations

from sdk_test_agent.docker_driver.docker_driver_models import BuildImageSpec
from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep

from ._utils import persist_text


class BuildImageStepExecutor:
    step_kind = PlanStepKind.BUILD_IMAGE

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.docker_driver is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="docker_driver is not configured")

        raw_spec = step.inputs.get("build_spec", step.inputs)
        spec = raw_spec if isinstance(raw_spec, BuildImageSpec) else BuildImageSpec(**{k: v for k, v in dict(raw_spec).items() if k in BuildImageSpec.__dataclass_fields__})
        result = context.docker_driver.build_image(spec)
        logs = "\n".join(str(entry) for entry in (getattr(result, "logs", []) or []))
        outputs = {"image_id": result.image_id, "tags": result.tags, "tag": spec.tag, "build_logs": logs}
        refs = []
        ref = persist_text(context, kind="build.log", name=f"{step.step_id}.build.log", text=logs)
        if ref:
            refs.append(ref)
        return StepExecutionResult(status=ExecutionStepStatus.SUCCEEDED, outputs=outputs, artifact_refs=refs, log_text=logs or None)
