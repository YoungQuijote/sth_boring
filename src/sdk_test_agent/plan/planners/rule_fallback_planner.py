from __future__ import annotations

from sdk_test_agent.plan.plan_context import PlannerInput
from sdk_test_agent.plan.plan_enums import PlannerKind
from sdk_test_agent.plan.plan_models import ExecutionPlan

from .demo_java_planner import DemoJavaPlanner


class RuleFallbackPlanner:
    name = "rule_fallback_planner"
    version = "0.1.0"
    kind = PlannerKind.RULE_FALLBACK

    def __init__(self) -> None:
        self._demo = DemoJavaPlanner()

    def plan(self, planner_input: PlannerInput) -> ExecutionPlan:
        plan = self._demo.plan(planner_input)
        plan.planner_kind = self.kind
        plan.planner_name = self.name
        plan.planner_version = self.version
        return plan
