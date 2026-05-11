from __future__ import annotations

from typing import Protocol

from sdk_test_agent.plan.plan_context import PlannerInput
from sdk_test_agent.plan.plan_models import ExecutionPlan, ExecutionPlanDraft


class BasePlanner(Protocol):
    name: str
    version: str
    kind: str

    def plan(self, planner_input: PlannerInput) -> ExecutionPlanDraft | ExecutionPlan:
        ...
