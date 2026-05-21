from __future__ import annotations

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionStepStatus
from sdk_test_agent.execution.execution_models import StepExecutionResult
from sdk_test_agent.inspection.package_inspector.package_inspector_models import JavaPackageInspectionInput
from sdk_test_agent.plan.plan_enums import PlanStepKind
from sdk_test_agent.plan.plan_models import PlanStep

from ._utils import get_input_or_variable, jsonable, persist_json


class InspectPackageStepExecutor:
    step_kind = PlanStepKind.INSPECT_PACKAGE

    def execute(self, step: PlanStep, context: ExecutionContext) -> StepExecutionResult:
        if context.package_inspector is None:
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="MissingDependency", error_message="package_inspector is not configured")

        language = get_input_or_variable(step.inputs, context, "language", "java")
        if language != "java":
            return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type="UnsupportedPackageLanguage", error_message=f"unsupported package language: {language}")

        data = get_input_or_variable(step.inputs, context, "inspection_input")
        if data is None:
            data = JavaPackageInspectionInput(
                sdk_name=get_input_or_variable(step.inputs, context, "sdk_name", "sdk"),
                sdk_version=get_input_or_variable(step.inputs, context, "sdk_version"),
                jar_bytes=get_input_or_variable(step.inputs, context, "jar_bytes", b""),
                pom_xml_bytes=get_input_or_variable(step.inputs, context, "pom_xml_bytes"),
                settings_xml_bytes=get_input_or_variable(step.inputs, context, "settings_xml_bytes"),
                jdk_bytes=get_input_or_variable(step.inputs, context, "jdk_bytes"),
            )

        report = context.package_inspector.inspect_java_package(data)
        outputs = {
            "package_report": report,
            "language": getattr(report, "language", language),
            "package_name": getattr(report, "package_name", None),
            "version": getattr(report, "version", None),
        }
        refs = []
        ref = persist_json(context, kind="report.json", name=f"{step.step_id}.package_report.json", payload=report)
        if ref:
            refs.append(ref)
        return StepExecutionResult(status=ExecutionStepStatus.SUCCEEDED, outputs=jsonable(outputs), artifact_refs=refs)
