from __future__ import annotations

from .execution_context import ExecutionContext
from .execution_engine import ExecutionEngine
from .execution_enums import ExecutionEventType, ExecutionRunStatus, ExecutionStepStatus
from .execution_errors import ExecutionDependencyError, ExecutionError, ExecutionUnsupportedStepKindError
from .execution_models import ExecutionRun, ExecutionRunResult, ExecutionStepRun, StepExecutionResult
from .step_executor_registry import StepExecutorRegistry
from .step_executors import (
    BuildImageStepExecutor,
    CollectArtifactStepExecutor,
    CreateRuntimeStepExecutor,
    ExecuteProbeStepExecutor,
    GenerateScriptStepExecutor,
    InspectEnvironmentStepExecutor,
    InspectPackageStepExecutor,
    RunCommandStepExecutor,
    RunTestStepExecutor,
    SummarizeReportStepExecutor,
)


def create_default_step_executor_registry() -> StepExecutorRegistry:
    registry = StepExecutorRegistry()
    for executor in (
        InspectPackageStepExecutor(),
        BuildImageStepExecutor(),
        CreateRuntimeStepExecutor(),
        InspectEnvironmentStepExecutor(),
        RunCommandStepExecutor(),
        ExecuteProbeStepExecutor(),
        CollectArtifactStepExecutor(),
        GenerateScriptStepExecutor(),
        RunTestStepExecutor(),
        SummarizeReportStepExecutor(),
    ):
        registry.register(executor)
    return registry


__all__ = [
    "ExecutionContext",
    "ExecutionDependencyError",
    "ExecutionEngine",
    "ExecutionError",
    "ExecutionEventType",
    "ExecutionRun",
    "ExecutionRunResult",
    "ExecutionRunStatus",
    "ExecutionStepRun",
    "ExecutionStepStatus",
    "ExecutionUnsupportedStepKindError",
    "StepExecutionResult",
    "StepExecutorRegistry",
    "create_default_step_executor_registry",
]
