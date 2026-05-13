from __future__ import annotations

import pytest

from sdk_test_agent.execution import ExecutionContext, ExecutionEngine, StepExecutorRegistry, create_default_step_executor_registry
from sdk_test_agent.execution.execution_enums import ExecutionRunStatus, ExecutionStepStatus
from sdk_test_agent.execution.execution_errors import ExecutionUnsupportedStepKindError
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.plan.plan_enums import PlannerKind, PlanStatus, StepFailurePolicy
from sdk_test_agent.plan.plan_models import ExecutionPlan, PlanStep


class FakeExecutor:
    def __init__(self, step_kind: str, status: str = ExecutionStepStatus.SUCCEEDED) -> None:
        self.step_kind = step_kind
        self.status = status

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        return StepExecutionResult(
            status=self.status,
            outputs={"value": step.step_id},
            error_type="FakeFailure" if self.status != ExecutionStepStatus.SUCCEEDED else None,
            error_message="fake failed" if self.status != ExecutionStepStatus.SUCCEEDED else None,
        )


class FakeArtifactRecord:
    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id


class FakeArtifactManager:
    def __init__(self) -> None:
        self.records = []

    def persist_artifact_bytes(self, **kwargs):
        self.records.append(kwargs)
        return FakeArtifactRecord(f"artifact_{len(self.records)}")


def _step(step_id: str, kind: str, *, depends_on=None, on_failure: str = StepFailurePolicy.ABORT) -> PlanStep:
    return PlanStep(step_id=step_id, title=step_id, kind=kind, intent="test", depends_on=depends_on or [], on_failure=on_failure)


def _plan(steps: list[PlanStep]) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan_1",
        task_id="task_1",
        task_type="sdk_deploy",
        goal="test execution",
        planner_kind=PlannerKind.DEMO,
        planner_name="test_planner",
        planner_version="v1",
        status=PlanStatus.VALIDATED,
        steps=steps,
    )


def _context(artifact_manager=None) -> ExecutionContext:
    return ExecutionContext(task_id="task_1", plan_id="plan_1", run_id="run_1", artifact_manager=artifact_manager)


def test_registry_lookup() -> None:
    registry = StepExecutorRegistry()
    registry.register(FakeExecutor("fake"))
    assert registry.get("fake").step_kind == "fake"
    assert registry.supported_step_kinds() == {"fake"}
    with pytest.raises(ExecutionUnsupportedStepKindError):
        registry.get("missing")


def test_execution_engine_successful_serial_execution() -> None:
    registry = StepExecutorRegistry()
    registry.register(FakeExecutor("a"))
    registry.register(FakeExecutor("b"))
    plan = _plan([_step("step_a", "a"), _step("step_b", "b", depends_on=["step_a"])])
    context = _context(FakeArtifactManager())

    result = ExecutionEngine(registry, time_func=lambda: 100).run(plan, context)

    assert result.status == ExecutionRunStatus.SUCCEEDED
    assert [sr.status for sr in result.run.step_runs] == [ExecutionStepStatus.SUCCEEDED, ExecutionStepStatus.SUCCEEDED]
    assert context.step_outputs["step_a"] == {"value": "step_a"}
    assert context.step_outputs["step_b"] == {"value": "step_b"}
    assert result.artifact_refs


def test_unsupported_step_kind_is_raised() -> None:
    plan = _plan([_step("step_missing", "missing")])
    with pytest.raises(ExecutionUnsupportedStepKindError):
        ExecutionEngine(StepExecutorRegistry()).run(plan, _context())


def test_dependency_skip_after_failed_continue_step() -> None:
    registry = StepExecutorRegistry()
    registry.register(FakeExecutor("bad", ExecutionStepStatus.FAILED))
    registry.register(FakeExecutor("after"))
    plan = _plan([
        _step("step_a", "bad", on_failure=StepFailurePolicy.CONTINUE),
        _step("step_b", "after", depends_on=["step_a"]),
    ])

    result = ExecutionEngine(registry).run(plan, _context())

    assert result.status == ExecutionRunStatus.SUCCEEDED
    assert [sr.status for sr in result.run.step_runs] == [ExecutionStepStatus.FAILED, ExecutionStepStatus.SKIPPED]
    assert "step_b" not in result.step_results


def test_failure_policy_abort_stops_run() -> None:
    registry = StepExecutorRegistry()
    registry.register(FakeExecutor("bad", ExecutionStepStatus.FAILED))
    registry.register(FakeExecutor("later"))
    plan = _plan([_step("step_a", "bad"), _step("step_b", "later")])

    result = ExecutionEngine(registry).run(plan, _context())

    assert result.status == ExecutionRunStatus.FAILED
    assert [sr.step_id for sr in result.run.step_runs] == ["step_a"]


def test_failure_policy_continue_allows_independent_later_steps() -> None:
    registry = StepExecutorRegistry()
    registry.register(FakeExecutor("bad", ExecutionStepStatus.FAILED))
    registry.register(FakeExecutor("later"))
    plan = _plan([_step("step_a", "bad", on_failure=StepFailurePolicy.CONTINUE), _step("step_b", "later")])

    result = ExecutionEngine(registry).run(plan, _context())

    assert result.status == ExecutionRunStatus.SUCCEEDED
    assert [sr.status for sr in result.run.step_runs] == [ExecutionStepStatus.FAILED, ExecutionStepStatus.SUCCEEDED]
    assert context_value(result, "step_b") == "step_b"


def test_failure_policy_request_replan() -> None:
    registry = StepExecutorRegistry()
    registry.register(FakeExecutor("bad", ExecutionStepStatus.FAILED))
    plan = _plan([_step("step_a", "bad", on_failure=StepFailurePolicy.REQUEST_REPLAN)])

    result = ExecutionEngine(registry, time_func=lambda: 123).run(plan, _context())

    assert result.status == ExecutionRunStatus.WAITING_REPLAN
    assert result.run.step_runs[0].status == ExecutionStepStatus.WAITING_REPLAN
    assert result.replan_request is not None
    assert result.replan_request.failed_step_id == "step_a"
    assert result.replan_request.parent_plan_id == "plan_1"


def test_default_registry_contains_v1_step_kinds() -> None:
    supported = create_default_step_executor_registry().supported_step_kinds()
    assert {"inspect_package", "build_image", "create_runtime", "inspect_environment", "run_command", "execute_probe", "collect_artifact"}.issubset(supported)


def context_value(result, step_id):
    return result.step_results[step_id].outputs["value"]


def test_v1_java_deploy_style_plan_smoke_connects_step_executors() -> None:
    from sdk_test_agent.docker_driver.docker_driver_models import BuildImageResult
    from sdk_test_agent.inspection.env_inspector.env_inspector_models import EnvInspectionReport
    from sdk_test_agent.inspection.inspection_enums import InspectionStatus, InspectionSubjectType
    from sdk_test_agent.inspection.package_inspector.package_inspector_models import PackageInspectionReport

    class FakePackageInspector:
        def inspect_java_package(self, data):
            return PackageInspectionReport(
                subject_type=InspectionSubjectType.PACKAGE,
                subject_name=data.sdk_name,
                status=InspectionStatus.SUCCESS,
                language="java",
                package_name=data.sdk_name,
            )

    class FakeDockerDriver:
        def build_image(self, spec):
            return BuildImageResult(image_id="img_1", tags=[spec.tag or "demo:latest"], logs=[{"stream": "built"}])

    class FakeContainer:
        container_id = "ctr_1"
        engine_id = "engine_1"
        metadata_json = "{}"

    class FakeRuntimeManager:
        def create_container(self, spec, owner_task_id=None):
            return FakeContainer()

    class FakeEnvInspector:
        def inspect_docker_env(self, data):
            return EnvInspectionReport(
                subject_type=InspectionSubjectType.ENVIRONMENT,
                subject_name=data.container_id,
                status=InspectionStatus.SUCCESS,
                readiness="ready",
                container_id=data.container_id,
            )

    class FakeCommandController:
        def execute_action(self, action, payload):
            return {"ok": True, "action": action, "data": {"exit_code": 0, "stdout": "ok", "stderr": ""}}

    steps = [
        _step("step_inspect_package", "inspect_package"),
        _step("step_build_image", "build_image", depends_on=["step_inspect_package"]),
        _step("step_create_runtime", "create_runtime", depends_on=["step_build_image"]),
        _step("step_inspect_environment", "inspect_environment", depends_on=["step_create_runtime"], on_failure=StepFailurePolicy.REQUEST_REPLAN),
        _step("step_probe", "execute_probe", depends_on=["step_inspect_environment"], on_failure=StepFailurePolicy.CONTINUE),
        _step("step_collect_artifact", "collect_artifact", depends_on=["step_probe"], on_failure=StepFailurePolicy.CONTINUE),
    ]
    steps[0].inputs.update({"sdk_name": "demo-sdk", "jar_bytes": b"jar"})
    steps[1].inputs.update({"build_spec": {"tag": "demo:latest", "dockerfile_text": "FROM scratch"}})
    steps[4].inputs.update({"probes": ["java -version", "pwd"]})

    context = _context(FakeArtifactManager())
    context.package_inspector = FakePackageInspector()
    context.docker_driver = FakeDockerDriver()
    context.runtime_manager = FakeRuntimeManager()
    context.env_inspector = FakeEnvInspector()
    context.command_controller = FakeCommandController()

    result = ExecutionEngine(create_default_step_executor_registry()).run(_plan(steps), context)

    assert result.status == ExecutionRunStatus.SUCCEEDED
    assert context.step_outputs["step_build_image"]["image_id"] == "img_1"
    assert context.step_outputs["step_create_runtime"]["container_id"] == "ctr_1"
    assert context.step_outputs["step_inspect_environment"]["readiness"] == "ready"
    assert context.step_outputs["step_collect_artifact"]["artifact_refs"]
