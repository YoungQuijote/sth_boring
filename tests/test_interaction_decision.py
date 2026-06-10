from __future__ import annotations

import pytest

from sdk_test_agent.agent_loop import (
    InteractionDecision,
    InteractionDecisionParseError,
    InteractionDecisionRequest,
    InteractionDecisionValidationError,
    InteractionDecisionValidator,
    LlmInteractionDecider,
)
from sdk_test_agent.llm import LlmResponse


class FakeLlmClient:
    def __init__(self, content: str):
        self.content = content
        self.request = None

    def complete(self, request):
        self.request = request
        return LlmResponse(content=self.content)


def valid_decision(**overrides):
    values = {"mode": "RETURN", "content": "hello", "confidence": 0.9, "reason": "greeting", "normalized_goal": None, "metadata": {}}
    values.update(overrides)
    return InteractionDecision(**values)


@pytest.mark.parametrize(
    "decision",
    [
        valid_decision(mode="UNKNOWN"),
        valid_decision(confidence=-0.1),
        valid_decision(confidence=1.1),
        valid_decision(mode="PLAN", normalized_goal=None),
        valid_decision(content=""),
        valid_decision(mode="REFUSE", content=""),
        valid_decision(mode="HUMAN", content=""),
        valid_decision(metadata=[]),
    ],
)
def test_validator_rejects_invalid_decisions(decision) -> None:
    with pytest.raises(InteractionDecisionValidationError):
        InteractionDecisionValidator().validate(decision)


def test_llm_decider_returns_valid_decision_and_forwards_protocol() -> None:
    client = FakeLlmClient('{"mode":"PLAN","content":"planning","confidence":0.8,"reason":"tool needed","normalized_goal":"show time","metadata":{}}')
    decision = LlmInteractionDecider(client, model_alias="deepseek", api_protocol="chat_completions").decide(InteractionDecisionRequest(raw_user_input="show time"))
    assert decision.mode == "PLAN"
    assert decision.normalized_goal == "show time"
    assert client.request.api_protocol == "chat_completions"
    assert client.request.response_format == "json_object"


@pytest.mark.parametrize("content", ["not json", "[]"])
def test_llm_decider_rejects_non_object_json(content: str) -> None:
    with pytest.raises(InteractionDecisionParseError):
        LlmInteractionDecider(FakeLlmClient(content)).decide(InteractionDecisionRequest(raw_user_input="hello"))


def test_llm_decider_does_not_repair_invalid_payload() -> None:
    client = FakeLlmClient('{"mode":"return","content":"hello","confidence":2,"reason":"greeting","normalized_goal":null,"metadata":{}}')
    with pytest.raises(InteractionDecisionValidationError):
        LlmInteractionDecider(client).decide(InteractionDecisionRequest(raw_user_input="hello"))


def test_llm_decider_rejects_missing_required_field() -> None:
    client = FakeLlmClient('{"mode":"RETURN","content":"hello","confidence":0.9,"reason":"greeting","normalized_goal":null}')
    with pytest.raises(InteractionDecisionValidationError, match="missing required fields: metadata"):
        LlmInteractionDecider(client).decide(InteractionDecisionRequest(raw_user_input="hello"))
