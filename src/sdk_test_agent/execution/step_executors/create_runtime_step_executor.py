from __future__ import annotations

from sdk_test_agent.docker_driver.docker_driver_models import ContainerCreateSpec
from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep

from ._utils import find_output


class CreateRuntimeStepExecutor:
    step_kind = PlanStepKind.CREATE_RUNTIME

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.runtime_manager is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="runtime_manager is not configured")

        image = step.inputs.get("image") or step.inputs.get("image_id") or find_output(context, "image_id")
        if not image:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingInput", error_message="image_id is required to create runtime")

        raw_spec = step.inputs.get("container_spec")
        if isinstance(raw_spec, ContainerCreateSpec):
            spec = raw_spec
        else:
            payload = dict(raw_spec or {})
            payload.setdefault("image", image)
            payload.setdefault("command", step.inputs.get("command", ["sleep", "3600"]))
            spec = ContainerCreateSpec(**{k: v for k, v in payload.items() if k in ContainerCreateSpec.__dataclass_fields__})

        container = context.runtime_manager.create_container(spec, owner_task_id=context.task_id)
        container_id = getattr(container, "container_id", None)
        context.runtime_refs[step.step_id] = container
        context.runtime_refs["latest_container_id"] = container_id

        outputs = {"container_id": container_id, "engine_id": getattr(container, "engine_id", None), "runtime_metadata": getattr(container, "metadata_json", None)}
        if step.inputs.get("create_deployment"):
            deployment = context.runtime_manager.create_deployment_record(**step.inputs["create_deployment"], image_id=image, container_id=container_id, task_id=context.task_id)
            outputs["deployment_id"] = getattr(deployment, "deployment_id", None)
        return StepExecutionResult(status=ExecutionStepStatus.SUCCEEDED, outputs=outputs)
