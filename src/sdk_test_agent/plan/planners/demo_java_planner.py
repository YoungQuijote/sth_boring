from __future__ import annotations

from time import time
from uuid import uuid4

from sdk_test_agent.plan.plan_context import PlannerInput
from sdk_test_agent.plan.plan_enums import PlanStatus, PlanStepKind, PlannerKind, StepFailurePolicy, StepRiskLevel
from sdk_test_agent.plan.plan_models import ExecutionPlan, PlanStep


class DemoJavaPlanner:
    name = "demo_java_planner"
    version = "0.1.0"
    kind = PlannerKind.DEMO

    def plan(self, planner_input: PlannerInput) -> ExecutionPlan:
        ctx = planner_input.base_context
        return ExecutionPlan(
            plan_id=f"plan_{uuid4().hex[:16]}",
            task_id=ctx.task_id,
            task_type=ctx.task_type,
            goal=ctx.goal,
            planner_kind=self.kind,
            planner_name=self.name,
            planner_version=self.version,
            status=PlanStatus.VALIDATED,
            steps=[
                PlanStep(
                    step_id="step_001",
                    title="Inspect Java package input",
                    kind=PlanStepKind.INSPECT_PACKAGE,
                    intent="Read or run Java package inspection before deployment.",
                    inputs={"language": "java"},
                    expected_outputs=["PackageInspectionReport"],
                    required_capabilities=["inspection.package.java"],
                    timeout_sec=30,
                    risk_level=StepRiskLevel.LOW,
                    on_failure=StepFailurePolicy.ABORT,
                ),
                PlanStep(
                    step_id="step_002",
                    title="Build runtime image",
                    kind=PlanStepKind.BUILD_IMAGE,
                    intent="Build a conservative Docker image for the provided Java jar.",
                    depends_on=["step_001"],
                    inputs={"strategy": "conservative_java_jar_runtime"},
                    expected_outputs=["BuildImageResult", "image_id"],
                    required_capabilities=["docker.build_image"],
                    timeout_sec=300,
                    retryable=True,
                    risk_level=StepRiskLevel.MEDIUM,
                    on_failure=StepFailurePolicy.ABORT,
                ),
                PlanStep(
                    step_id="step_003",
                    title="Create runtime container",
                    kind=PlanStepKind.CREATE_RUNTIME,
                    intent="Create and start a Docker container for the built image.",
                    depends_on=["step_002"],
                    inputs={"runtime": "docker"},
                    expected_outputs=["container_id", "deployment_record"],
                    required_capabilities=["runtime.create_container"],
                    timeout_sec=120,
                    retryable=True,
                    risk_level=StepRiskLevel.MEDIUM,
                    on_failure=StepFailurePolicy.ABORT,
                ),
                PlanStep(
                    step_id="step_004",
                    title="Inspect runtime environment",
                    kind=PlanStepKind.INSPECT_ENVIRONMENT,
                    intent="Run read-only probes inside the container to verify runtime basics.",
                    depends_on=["step_003"],
                    inputs={"probes": ["java -version", "pwd", "ls"]},
                    expected_outputs=["EnvInspectionReport"],
                    required_capabilities=["inspection.env.docker"],
                    timeout_sec=60,
                    retryable=True,
                    risk_level=StepRiskLevel.LOW,
                    on_failure=StepFailurePolicy.REQUEST_REPLAN,
                ),
                PlanStep(
                    step_id="step_005",
                    title="Collect deployment artifacts",
                    kind=PlanStepKind.COLLECT_ARTIFACT,
                    intent="Collect plan, build, probe and deployment metadata references.",
                    depends_on=["step_004"],
                    expected_outputs=["artifact_refs"],
                    required_capabilities=["artifact.collect"],
                    timeout_sec=60,
                    risk_level=StepRiskLevel.LOW,
                    on_failure=StepFailurePolicy.CONTINUE,
                ),
            ],
            assumptions=["The input jar is already compiled.", "The MVP does not run Maven source builds."],
            risk_notes=["Deployment uses a conservative runtime image and may need later refinement."],
            global_constraints=ctx.constraints,
            created_at=int(time()),
        )
