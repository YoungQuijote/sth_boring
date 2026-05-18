from __future__ import annotations

from .capability_enums import CapabilityRiskLevel, CapabilityVisibility
from .capability_io_models import (
    BuildImageInput,
    BuildImageOutput,
    CollectArtifactInput,
    CollectArtifactOutput,
    CreateRuntimeInput,
    CreateRuntimeOutput,
    EmptyPlaceholderInput,
    EmptyPlaceholderOutput,
    ExecuteProbeInput,
    ExecuteProbeOutput,
    InspectEnvironmentInput,
    InspectEnvironmentOutput,
    InspectPackageInput,
    InspectPackageOutput,
    RunCommandInput,
    RunCommandOutput,
)
from .capability_models import CapabilityDescriptor
from .capability_registry import CapabilityRegistry


def _schema(model) -> dict:
    return model.model_json_schema()


INSPECT_PACKAGE_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.inspect_package.v1",
    version="1.0.0",
    step_kind="inspect_package",
    executor_name="InspectPackageStepExecutor",
    owner_module="inspection.package_inspector",
    name="Inspect package input",
    description="Inspect package input metadata and produce a package report.",
    input_model_ref="InspectPackageInput",
    output_model_ref="InspectPackageOutput",
    input_schema=_schema(InspectPackageInput),
    output_schema=_schema(InspectPackageOutput),
    required_context_keys=("package_inspector",),
    risk_level=CapabilityRiskLevel.LOW,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=({"step_id": "inspect_package", "kind": "inspect_package", "inputs": {"package_type": "java", "input_refs": {"jar": "artifact_jar"}}},),
    tags=("inspection", "package"),
)

BUILD_IMAGE_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.build_image.docker.v1",
    version="1.0.0",
    step_kind="build_image",
    executor_name="BuildImageStepExecutor",
    owner_module="docker_driver",
    name="Build Docker image",
    description="Build a Docker image from an artifact-backed Dockerfile and optional build context.",
    input_model_ref="BuildImageInput",
    output_model_ref="BuildImageOutput",
    input_schema=_schema(BuildImageInput),
    output_schema=_schema(BuildImageOutput),
    required_context_keys=("docker_driver",),
    risk_level=CapabilityRiskLevel.MEDIUM,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=(
        {
            "step_id": "build_image",
            "kind": "build_image",
            "inputs": {"image_name": "demo-sdk", "tag": "latest", "dockerfile": {"artifact_ref": "artifact_dockerfile"}},
        },
    ),
    tags=("docker", "build"),
)

CREATE_RUNTIME_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.create_runtime.docker.v1",
    version="1.0.0",
    step_kind="create_runtime",
    executor_name="CreateRuntimeStepExecutor",
    owner_module="control_plane.runtime_manager",
    name="Create runtime",
    description="Create and optionally start a managed runtime from an image reference.",
    input_model_ref="CreateRuntimeInput",
    output_model_ref="CreateRuntimeOutput",
    input_schema=_schema(CreateRuntimeInput),
    output_schema=_schema(CreateRuntimeOutput),
    required_context_keys=("runtime_manager",),
    risk_level=CapabilityRiskLevel.MEDIUM,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=({"step_id": "create_runtime", "kind": "create_runtime", "inputs": {"image_ref": "demo-sdk:latest", "start": True}},),
    tags=("runtime", "docker"),
)

INSPECT_ENVIRONMENT_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.inspect_environment.docker.v1",
    version="1.0.0",
    step_kind="inspect_environment",
    executor_name="InspectEnvironmentStepExecutor",
    owner_module="inspection.env_inspector",
    name="Inspect environment",
    description="Inspect runtime readiness and environment details with read-only probes.",
    input_model_ref="InspectEnvironmentInput",
    output_model_ref="InspectEnvironmentOutput",
    input_schema=_schema(InspectEnvironmentInput),
    output_schema=_schema(InspectEnvironmentOutput),
    required_context_keys=("env_inspector",),
    risk_level=CapabilityRiskLevel.LOW,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=({"step_id": "inspect_environment", "kind": "inspect_environment", "inputs": {"runtime_ref": "runtime_1", "probes": ["java -version"]}},),
    tags=("inspection", "environment"),
)

RUN_COMMAND_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.run_command.inspect_exec.v1",
    version="1.0.0",
    step_kind="run_command",
    executor_name="RunCommandStepExecutor",
    owner_module="cmd_ctrl",
    name="Run readonly command",
    description="Run a low-risk readonly command through cmd_ctrl InspectExecOperator.",
    input_model_ref="RunCommandInput",
    output_model_ref="RunCommandOutput",
    input_schema=_schema(RunCommandInput),
    output_schema=_schema(RunCommandOutput),
    required_context_keys=("command_controller",),
    risk_level=CapabilityRiskLevel.LOW,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=(
        {"step_id": "check_java_version", "kind": "run_command", "inputs": {"action": "inspect_exec", "payload": {"cmd": ["java", "-version"], "timeout_sec": 30}}},
    ),
    tags=("cmd_ctrl", "readonly", "inspect"),
)

EXECUTE_PROBE_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.execute_probe.inspect_exec.v1",
    version="1.0.0",
    step_kind="execute_probe",
    executor_name="ExecuteProbeStepExecutor",
    owner_module="cmd_ctrl",
    name="Execute readiness probe",
    description="Run a named read-only readiness probe through cmd_ctrl InspectExecOperator.",
    input_model_ref="ExecuteProbeInput",
    output_model_ref="ExecuteProbeOutput",
    input_schema=_schema(ExecuteProbeInput),
    output_schema=_schema(ExecuteProbeOutput),
    required_context_keys=("command_controller",),
    risk_level=CapabilityRiskLevel.LOW,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=({"step_id": "probe_pwd", "kind": "execute_probe", "inputs": {"probe_name": "pwd", "payload": {"cmd": ["pwd"]}}},),
    tags=("probe", "readonly"),
)

COLLECT_ARTIFACT_CAPABILITY = CapabilityDescriptor(
    capability_id="cap.collect_artifact.v1",
    version="1.0.0",
    step_kind="collect_artifact",
    executor_name="CollectArtifactStepExecutor",
    owner_module="artifact_manager",
    name="Collect artifact",
    description="Persist an execution artifact reference through artifact_manager owned orchestration.",
    input_model_ref="CollectArtifactInput",
    output_model_ref="CollectArtifactOutput",
    input_schema=_schema(CollectArtifactInput),
    output_schema=_schema(CollectArtifactOutput),
    required_context_keys=("artifact_manager",),
    risk_level=CapabilityRiskLevel.LOW,
    visibility=CapabilityVisibility.PLANNER_VISIBLE,
    examples=({"step_id": "collect_log", "kind": "collect_artifact", "inputs": {"source_path": "logs/app.log", "artifact_kind": "exec.log", "name": "app.log"}},),
    tags=("artifact", "reporting"),
)


def _placeholder(step_kind: str, executor_name: str, name: str) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=f"cap.{step_kind}.placeholder.v1",
        version="0.1.0",
        step_kind=step_kind,
        executor_name=executor_name,
        owner_module="execution.step_executors",
        name=name,
        description=f"Placeholder for future {name.lower()} integration.",
        input_model_ref="EmptyPlaceholderInput",
        output_model_ref="EmptyPlaceholderOutput",
        input_schema=_schema(EmptyPlaceholderInput),
        output_schema=_schema(EmptyPlaceholderOutput),
        required_context_keys=(),
        risk_level=CapabilityRiskLevel.MEDIUM,
        visibility=CapabilityVisibility.PLANNER_VISIBLE,
        default_enabled=False,
        is_placeholder=True,
        tags=("placeholder",),
    )


PARSE_TEXT_CAPABILITY = _placeholder("parse_text", "ParseTextStepExecutor", "Parse text")
GENERATE_SCRIPT_CAPABILITY = _placeholder("generate_script", "GenerateScriptStepExecutor", "Generate script")
RUN_TEST_CAPABILITY = _placeholder("run_test", "RunTestStepExecutor", "Run test")
SUMMARIZE_REPORT_CAPABILITY = _placeholder("summarize_report", "SummarizeReportStepExecutor", "Summarize report")

BUILTIN_CAPABILITIES = (
    INSPECT_PACKAGE_CAPABILITY,
    BUILD_IMAGE_CAPABILITY,
    CREATE_RUNTIME_CAPABILITY,
    INSPECT_ENVIRONMENT_CAPABILITY,
    RUN_COMMAND_CAPABILITY,
    EXECUTE_PROBE_CAPABILITY,
    COLLECT_ARTIFACT_CAPABILITY,
    PARSE_TEXT_CAPABILITY,
    GENERATE_SCRIPT_CAPABILITY,
    RUN_TEST_CAPABILITY,
    SUMMARIZE_REPORT_CAPABILITY,
)


def build_builtin_capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for descriptor in BUILTIN_CAPABILITIES:
        registry.register(descriptor)
    return registry
