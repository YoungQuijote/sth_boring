from __future__ import annotations


class ExecutionRunStatus:
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_REPLAN = "waiting_replan"


class ExecutionStepStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    WAITING_REPLAN = "waiting_replan"


class ExecutionEventType:
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    STEP_STARTED = "step_started"
    STEP_FINISHED = "step_finished"
    STEP_FAILED = "step_failed"
    REPLAN_REQUESTED = "replan_requested"
