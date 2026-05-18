from __future__ import annotations


class PlannerKind:
    FAST = "fast"
    LLM = "llm"
    RULE_FALLBACK = "rule_fallback"
    DEMO = "demo"


class PlanStatus:
    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"
    FROZEN = "frozen"


class PlanStepKind:
    INSPECT_PACKAGE = "inspect_package"
    PARSE_TEXT = "parse_text"
    BUILD_IMAGE = "build_image"
    CREATE_RUNTIME = "create_runtime"
    INSPECT_ENVIRONMENT = "inspect_environment"
    RUN_COMMAND = "run_command"
    EXECUTE_PROBE = "execute_probe"
    GENERATE_SCRIPT = "generate_script"
    RUN_TEST = "run_test"
    COLLECT_ARTIFACT = "collect_artifact"
    SUMMARIZE_REPORT = "summarize_report"


class StepRiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StepFailurePolicy:
    ABORT = "abort"
    CONTINUE = "continue"
    FALLBACK = "fallback"
    REQUEST_REPLAN = "request_replan"


class ValidationSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationStatus:
    PASSED = "passed"
    FAILED = "failed"


SUPPORTED_PLAN_STEP_KINDS = {
    PlanStepKind.INSPECT_PACKAGE,
    PlanStepKind.PARSE_TEXT,
    PlanStepKind.BUILD_IMAGE,
    PlanStepKind.CREATE_RUNTIME,
    PlanStepKind.INSPECT_ENVIRONMENT,
    PlanStepKind.RUN_COMMAND,
    PlanStepKind.EXECUTE_PROBE,
    PlanStepKind.GENERATE_SCRIPT,
    PlanStepKind.RUN_TEST,
    PlanStepKind.COLLECT_ARTIFACT,
    PlanStepKind.SUMMARIZE_REPORT,
}

VALID_RISK_LEVELS = {StepRiskLevel.LOW, StepRiskLevel.MEDIUM, StepRiskLevel.HIGH}
VALID_FAILURE_POLICIES = {
    StepFailurePolicy.ABORT,
    StepFailurePolicy.CONTINUE,
    StepFailurePolicy.FALLBACK,
    StepFailurePolicy.REQUEST_REPLAN,
}
