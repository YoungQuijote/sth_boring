from __future__ import annotations

from dataclasses import dataclass

from sdk_test_agent.plan.plan_enums import StepFailurePolicy


@dataclass(slots=True)
class FailurePolicyDecision:
    action: str
    should_stop: bool
    should_request_replan: bool = False


def decide_failure_action(on_failure: str) -> FailurePolicyDecision:
    if on_failure == StepFailurePolicy.CONTINUE:
        return FailurePolicyDecision(action=on_failure, should_stop=False)
    if on_failure == StepFailurePolicy.REQUEST_REPLAN:
        return FailurePolicyDecision(action=on_failure, should_stop=True, should_request_replan=True)
    # Temporarily not implemented in v1: fallback graph execution. Reserved for future extension.
    return FailurePolicyDecision(action=on_failure, should_stop=True)
