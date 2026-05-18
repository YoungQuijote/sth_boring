from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Callable

from sdk_test_agent.execution.execution_context import ExecutionContext
from sdk_test_agent.execution.execution_enums import ExecutionRunStatus, ExecutionStepStatus
from sdk_test_agent.execution.execution_models import ExecutionRun, ExecutionRunResult, ExecutionStepRun, StepExecutionResult
from sdk_test_agent.execution.step_executor_registry import StepExecutorRegistry
from sdk_test_agent.plan.plan_enums import StepFailurePolicy
from sdk_test_agent.plan.plan_models import ExecutionPlan, PlanStep, ReplanRequest


class ExecutionEngine:
    """Serial interpreter for validated ExecutionPlan instances."""

    def __init__(self, registry: StepExecutorRegistry, time_func: Callable[[], int] | None = None) -> None:
        self.registry = registry
        self.time_func = time_func or (lambda: int(time.time() * 1000))

    def run(self, plan: ExecutionPlan, context: ExecutionContext) -> ExecutionRunResult:
        run = self._create_run(plan, context)
        step_results: dict[str, StepExecutionResult] = {}
        step_status: dict[str, str] = {}
        replan_request: ReplanRequest | None = None

        for step in plan.steps:
            if not self._dependencies_satisfied(step, step_status):
                step_run = self._mark_skipped_due_to_dependency(step, run)
                run.step_runs.append(step_run)
                step_status[step.step_id] = ExecutionStepStatus.SKIPPED
                continue

            executor = self.registry.get(step.kind)
            step_run = self._start_step_run(step, run)

            try:
                result = executor.execute(step, context)
            except Exception as exc:  # noqa: BLE001 - execution result should preserve tool failures.
                result = self._result_from_exception(exc)

            self._finish_step_run(step_run, result, context)
            run.step_runs.append(step_run)
            step_results[step.step_id] = result
            step_status[step.step_id] = result.status

            if result.status == ExecutionStepStatus.SUCCEEDED:
                context.step_outputs[step.step_id] = result.outputs
                continue

            if step.on_failure == StepFailurePolicy.CONTINUE:
                continue

            if step.on_failure == StepFailurePolicy.REQUEST_REPLAN:
                result.status = ExecutionStepStatus.WAITING_REPLAN
                step_run.status = ExecutionStepStatus.WAITING_REPLAN
                step_status[step.step_id] = ExecutionStepStatus.WAITING_REPLAN
                replan_request = self._build_replan_request(plan, step, result, context)
                run.status = ExecutionRunStatus.WAITING_REPLAN
                run.finished_at = self.time_func()
                run.result_summary = f"Execution waiting for replan after step {step.step_id}."
                refs = self._finish_artifact_recording(run, step_results, context)
                return ExecutionRunResult(run=run, status=run.status, step_results=step_results, replan_request=replan_request, artifact_refs=refs)

            # v1 treats fallback as abort unless a future fallback graph extension is supplied.
            run.status = ExecutionRunStatus.FAILED
            run.finished_at = self.time_func()
            run.result_summary = f"Execution failed at step {step.step_id}: {result.error_message or result.status}"
            refs = self._finish_artifact_recording(run, step_results, context)
            return ExecutionRunResult(run=run, status=run.status, step_results=step_results, artifact_refs=refs)

        run.status = ExecutionRunStatus.SUCCEEDED
        run.finished_at = self.time_func()
        run.result_summary = f"Execution succeeded with {len(run.step_runs)} step run(s)."
        refs = self._finish_artifact_recording(run, step_results, context)
        return ExecutionRunResult(run=run, status=run.status, step_results=step_results, artifact_refs=refs)

    def _create_run(self, plan: ExecutionPlan, context: ExecutionContext) -> ExecutionRun:
        started_at = self.time_func()
        return ExecutionRun(
            run_id=context.run_id,
            task_id=context.task_id or plan.task_id,
            plan_id=context.plan_id or plan.plan_id,
            status=ExecutionRunStatus.RUNNING,
            started_at=started_at,
            metadata={"planner_name": plan.planner_name, "planner_version": plan.planner_version},
        )

    @staticmethod
    def _dependencies_satisfied(step: PlanStep, step_status: dict[str, str]) -> bool:
        return all(step_status.get(dep) == ExecutionStepStatus.SUCCEEDED for dep in step.depends_on)

    def _mark_skipped_due_to_dependency(self, step: PlanStep, run: ExecutionRun) -> ExecutionStepRun:
        now = self.time_func()
        return ExecutionStepRun(
            step_run_id=self._new_id("step_run"),
            run_id=run.run_id,
            step_id=step.step_id,
            step_kind=step.kind,
            status=ExecutionStepStatus.SKIPPED,
            started_at=now,
            finished_at=now,
            duration_ms=0,
            inputs_snapshot=dict(step.inputs),
            error_type="DependencyNotSatisfied",
            error_message="one or more dependencies did not succeed",
        )

    def _start_step_run(self, step: PlanStep, run: ExecutionRun) -> ExecutionStepRun:
        return ExecutionStepRun(
            step_run_id=self._new_id("step_run"),
            run_id=run.run_id,
            step_id=step.step_id,
            step_kind=step.kind,
            status=ExecutionStepStatus.RUNNING,
            started_at=self.time_func(),
            inputs_snapshot=dict(step.inputs),
        )

    def _finish_step_run(self, step_run: ExecutionStepRun, result: StepExecutionResult, context: ExecutionContext) -> None:
        step_run.finished_at = self.time_func()
        if step_run.started_at is not None:
            step_run.duration_ms = max(0, step_run.finished_at - step_run.started_at)
        step_run.status = result.status
        step_run.outputs = result.outputs
        step_run.artifact_refs = list(result.artifact_refs)
        step_run.error_type = result.error_type
        step_run.error_message = result.error_message
        step_run.metadata = dict(result.metadata)

        if result.stdout is not None:
            step_run.stdout_ref = self._persist_text(context, "exec.stdout", f"{step_run.step_id}.stdout.txt", result.stdout)
        if result.stderr is not None:
            step_run.stderr_ref = self._persist_text(context, "exec.stderr", f"{step_run.step_id}.stderr.txt", result.stderr)
        if result.log_text is not None:
            step_run.log_ref = self._persist_text(context, "exec.log", f"{step_run.step_id}.log.txt", result.log_text)
        for ref in (step_run.stdout_ref, step_run.stderr_ref, step_run.log_ref):
            if ref:
                step_run.artifact_refs.append(ref)
                result.artifact_refs.append(ref)

    @staticmethod
    def _result_from_exception(exc: Exception) -> StepExecutionResult:
        return StepExecutionResult(status=ExecutionStepStatus.FAILED, error_type=exc.__class__.__name__, error_message=str(exc))

    def _build_replan_request(self, plan: ExecutionPlan, step: PlanStep, result: StepExecutionResult, context: ExecutionContext) -> ReplanRequest:
        observations = [
            f"step {step.step_id} ({step.kind}) failed with {result.error_type or result.status}: {result.error_message or ''}".strip(),
        ]
        env_ref = context.artifact_refs.get("latest_env_report")
        return ReplanRequest(
            task_id=context.task_id or plan.task_id,
            parent_plan_id=plan.plan_id,
            reason=result.error_message or f"step {step.step_id} requested replan",
            failed_step_id=step.step_id,
            execution_observations=observations,
            latest_env_report_ref=env_ref,
            latest_artifact_refs=list(context.artifact_refs.values()),
            metadata={"step_outputs": context.step_outputs, "run_id": context.run_id},
            created_at=self.time_func(),
        )

    def _finish_artifact_recording(self, run: ExecutionRun, step_results: dict[str, StepExecutionResult], context: ExecutionContext) -> list[str]:
        payload = {
            "run": self._to_jsonable(run),
            "step_results": self._to_jsonable(step_results),
        }
        ref = self._persist_text(context, "report.json", f"{run.run_id}.execution_summary.json", json.dumps(payload, sort_keys=True, default=str), mime_type="application/json")
        return [ref] if ref else []

    def _persist_text(self, context: ExecutionContext, kind: str, name: str, text: str, mime_type: str = "text/plain") -> str | None:
        manager = context.artifact_manager
        if manager is None:
            return None
        try:
            record = manager.persist_artifact_bytes(
                task_id=context.task_id,
                stage_id=None,
                kind=kind,
                name=name,
                content=text.encode("utf-8"),
                subdir="outputs",
                mime_type=mime_type,
                created_by_action="execution",
            )
        except TypeError:
            record = manager.persist_artifact_bytes(context.task_id, None, kind, name, text.encode("utf-8"), "outputs")
        ref = getattr(record, "artifact_id", None) or getattr(record, "storage_path", None) or str(record)
        context.artifact_refs[name] = ref
        return ref

    @staticmethod
    def _to_jsonable(value):
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return {k: ExecutionEngine._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ExecutionEngine._to_jsonable(v) for v in value]
        return value

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:16]}"
