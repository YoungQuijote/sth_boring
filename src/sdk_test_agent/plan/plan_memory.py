from __future__ import annotations

from dataclasses import asdict
from typing import Any, Protocol
from uuid import uuid4

from .plan_context import RetrievedPlanMemory
from .plan_models import ExecutionPlan


class PlanMemoryStore(Protocol):
    def save_successful_plan(
        self,
        task_id: str,
        task_type: str,
        goal: str,
        plan: ExecutionPlan,
        success_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        ...

    def search_similar_plans(self, task_type: str, query_text: str, limit: int = 5) -> list[RetrievedPlanMemory]:
        ...


class InMemoryPlanMemoryStore:
    def __init__(self) -> None:
        self._items: list[RetrievedPlanMemory] = []

    def save_successful_plan(
        self,
        task_id: str,
        task_type: str,
        goal: str,
        plan: ExecutionPlan,
        success_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        memory_id = f"memory_{uuid4().hex[:16]}"
        item = RetrievedPlanMemory(
            memory_id=memory_id,
            task_type=task_type,
            similarity=1.0,
            plan_summary=goal,
            plan_json=asdict(plan),
            success_score=success_score,
            source_task_id=task_id,
            metadata=metadata or {},
        )
        self._items.append(item)
        return memory_id

    def search_similar_plans(self, task_type: str, query_text: str, limit: int = 5) -> list[RetrievedPlanMemory]:
        q_words = set(query_text.lower().split())
        scored: list[RetrievedPlanMemory] = []
        for item in self._items:
            if item.task_type != task_type:
                continue
            words = set(item.plan_summary.lower().split())
            similarity = (len(q_words & words) / max(len(q_words | words), 1)) if q_words or words else 0.0
            scored.append(
                RetrievedPlanMemory(
                    memory_id=item.memory_id,
                    task_type=item.task_type,
                    similarity=similarity,
                    plan_summary=item.plan_summary,
                    plan_json=item.plan_json,
                    success_score=item.success_score,
                    source_task_id=item.source_task_id,
                    metadata=item.metadata,
                )
            )
        return sorted(scored, key=lambda x: (x.similarity, x.success_score or 0.0), reverse=True)[:limit]
