from __future__ import annotations

from sdk_test_agent.plan.plan_context import PlanContextBase, PlannerInput, RetrievedPlanMemory
from sdk_test_agent.plan.plan_enums import PlannerKind
from sdk_test_agent.plan.plan_memory import InMemoryPlanMemoryStore, PlanMemoryStore
from sdk_test_agent.plan.plan_models import ExecutionPlanDraft, PlanStep


class FastPlanner:
    name = "fast_planner"
    version = "0.1.0"
    kind = PlannerKind.FAST

    def __init__(self, memory_store: PlanMemoryStore | None = None) -> None:
        self.memory_store = memory_store or InMemoryPlanMemoryStore()

    def retrieve(self, context: PlanContextBase) -> list[RetrievedPlanMemory]:
        return self.memory_store.search_similar_plans(context.task_type, context.goal)

    def plan(self, planner_input: PlannerInput) -> ExecutionPlanDraft | None:
        memories = self.retrieve(planner_input.base_context)
        if not memories:
            return None
        memory = memories[0]
        steps = [PlanStep(**step) for step in memory.plan_json.get("steps", [])]
        return ExecutionPlanDraft(
            task_id=planner_input.base_context.task_id,
            task_type=planner_input.base_context.task_type,
            goal=planner_input.base_context.goal,
            planner_name=self.name,
            planner_version=self.version,
            plan_summary=f"Recalled plan from {memory.memory_id}: {memory.plan_summary}",
            steps=steps,
            metadata={"memory_id": memory.memory_id, "similarity": memory.similarity},
        )
