from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from sdk_test_agent.plan.plan_enums import PlannerKind, PlanStatus
from sdk_test_agent.plan.plan_models import ExecutionPlan, ExecutionPlanDraft


class PlanFinalizer:
    """Compile ExecutionPlanDraft into system-side ExecutionPlan.

    V1 boundary:
    - inject trusted system metadata;
    - copy draft business fields as-is;
    - bind capability/artifact/revision metadata;
    - do not validate, normalize, repair, or execute plan steps.
    """

    def __init__(
        self,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._id_factory = id_factory or self._default_id_factory
        self._clock = clock or self._default_clock

    def finalize(
        self,
        draft: ExecutionPlanDraft,
        *,
        planner_kind: str = PlannerKind.LLM,
        global_constraints: dict[str, Any] | None = None,
        parent_plan_id: str | None = None,
        revision_no: int = 0,
        capability_snapshot: Any | None = None,
        capability_resolution_record: Any | None = None,
        artifact_refs: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        plan_metadata: dict[str, Any] = {
            "plan_summary": draft.plan_summary,
            "draft_metadata": draft.metadata,
            "raw_llm_output": draft.raw_llm_output,
        }

        if capability_snapshot is not None:
            plan_metadata["capability_snapshot_id"] = capability_snapshot.snapshot_id
            plan_metadata["capability_digest"] = capability_snapshot.capability_digest

        if capability_resolution_record is not None:
            plan_metadata["capability_resolution_record_id"] = capability_resolution_record.record_id

        if artifact_refs:
            plan_metadata["artifact_refs"] = dict(artifact_refs)

        if metadata:
            plan_metadata.update(metadata)

        return ExecutionPlan(
            plan_id=self._id_factory(),
            task_id=draft.task_id,
            task_type=draft.task_type,
            goal=draft.goal,
            planner_kind=planner_kind,
            planner_name=draft.planner_name,
            planner_version=draft.planner_version,
            status=PlanStatus.DRAFT,
            # Important: copy as-is. Do not mutate step fields in PlanFinalizer v1.
            steps=list(draft.steps),
            assumptions=draft.assumptions,
            missing_information=draft.missing_information,
            risk_notes=draft.risk_notes,
            global_constraints=global_constraints or {},
            plan_metadata=plan_metadata,
            parent_plan_id=parent_plan_id,
            revision_no=revision_no,
            created_at=self._clock(),
        )

    @staticmethod
    def _default_id_factory() -> str:
        return f"plan_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def _default_clock() -> int:
        return int(time.time())
