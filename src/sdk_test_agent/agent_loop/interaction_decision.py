from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from sdk_test_agent.llm.llm_models import LlmMessage, LlmRequest
from sdk_test_agent.llm.response_parser import LlmJsonResponseParser

InteractionMode = Literal["PLAN", "RETURN", "REFUSE", "HUMAN"]


class InteractionDecisionError(Exception):
    """Base error raised by the interaction decision module."""


class InteractionDecisionParseError(InteractionDecisionError):
    """Raised when the LLM response is not a JSON object."""


class InteractionDecisionValidationError(InteractionDecisionError):
    """Raised when a parsed interaction decision violates the v1 contract."""


@dataclass(slots=True)
class InteractionDecisionRequest:
    raw_user_input: str
    task_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    conversation_summary: str | None = None
    system_capability_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InteractionDecision:
    mode: InteractionMode
    content: str
    confidence: float
    reason: str
    normalized_goal: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class InteractionDecider(Protocol):
    def decide(self, request: InteractionDecisionRequest) -> InteractionDecision:
        ...


class InteractionDecisionValidator:
    allowed_modes = {"PLAN", "RETURN", "REFUSE", "HUMAN"}

    def validate(self, decision: InteractionDecision) -> None:
        if decision.mode not in self.allowed_modes:
            raise InteractionDecisionValidationError(f"unsupported interaction mode: {decision.mode!r}")
        if not isinstance(decision.content, str):
            raise InteractionDecisionValidationError("content must be a string")
        if not isinstance(decision.reason, str) or not decision.reason.strip():
            raise InteractionDecisionValidationError("reason must be a non-empty string")
        if isinstance(decision.confidence, bool) or not isinstance(decision.confidence, (int, float)):
            raise InteractionDecisionValidationError("confidence must be a number")
        if not 0.0 <= decision.confidence <= 1.0:
            raise InteractionDecisionValidationError("confidence must be between 0.0 and 1.0")
        if not isinstance(decision.metadata, dict):
            raise InteractionDecisionValidationError("metadata must be an object")
        if decision.normalized_goal is not None and not isinstance(decision.normalized_goal, str):
            raise InteractionDecisionValidationError("normalized_goal must be a string or null")
        if decision.mode == "PLAN" and (not isinstance(decision.normalized_goal, str) or not decision.normalized_goal.strip()):
            raise InteractionDecisionValidationError("PLAN requires a non-empty normalized_goal")
        if decision.mode in {"RETURN", "REFUSE", "HUMAN"} and not decision.content.strip():
            raise InteractionDecisionValidationError(f"{decision.mode} requires non-empty content")


class LlmInteractionDecider:
    name = "llm_interaction_decider"
    version = "0.1.0"

    def __init__(
        self,
        llm_client,
        *,
        model: str | None = None,
        model_alias: str | None = None,
        api_protocol: str | None = None,
        temperature: float = 0.0,
        json_parser=None,
        validator=None,
    ) -> None:
        self.llm_client = llm_client
        self.model = model or "interaction-decision-model"
        self.model_alias = model_alias
        self.api_protocol = api_protocol
        self.temperature = temperature
        self.json_parser = json_parser or LlmJsonResponseParser()
        self.validator = validator or InteractionDecisionValidator()

    def decide(self, request: InteractionDecisionRequest) -> InteractionDecision:
        response = self.llm_client.complete(
            LlmRequest(
                model_alias=self.model_alias,
                model=None if self.model_alias else self.model,
                api_protocol=self.api_protocol,
                messages=[LlmMessage(role="user", content=build_interaction_decision_prompt(request))],
                response_format="json_object",
                temperature=self.temperature,
                metadata={"decider": self.name},
            )
        )
        try:
            payload = self.json_parser.parse_json_object(response)
        except Exception as exc:
            raise InteractionDecisionParseError("failed to parse interaction decision as a JSON object") from exc

        decision = self._from_payload(payload)
        self.validator.validate(decision)
        return decision

    @staticmethod
    def _from_payload(payload: dict[str, Any]) -> InteractionDecision:
        required = ("mode", "content", "confidence", "reason", "normalized_goal", "metadata")
        missing = [field_name for field_name in required if field_name not in payload]
        if missing:
            raise InteractionDecisionValidationError(f"missing required fields: {', '.join(missing)}")
        return InteractionDecision(
            mode=payload["mode"],
            content=payload["content"],
            confidence=payload["confidence"],
            reason=payload["reason"],
            normalized_goal=payload["normalized_goal"],
            metadata=payload["metadata"],
        )


def build_interaction_decision_prompt(request: InteractionDecisionRequest) -> str:
    context_lines = [f"raw_user_input: {request.raw_user_input}"]
    for name in ("task_id", "session_id", "user_id", "conversation_summary", "system_capability_summary"):
        value = getattr(request, name)
        if value is not None:
            context_lines.append(f"{name}: {value}")

    if request.metadata:
        context_lines.append(f"metadata: {json.dumps(request.metadata, ensure_ascii=False, sort_keys=True, default=str)}")

    return """You are the interaction decision module for SdkTestAgent.
Decide how the system should handle the user's input.

Allowed modes:
- PLAN: enter task planning and execution.
- RETURN: answer directly in natural language; no planning or execution is needed.
- REFUSE: refuse the request.
- HUMAN: pause for human intervention, approval, login, or permission.

Return strict JSON only with exactly these required fields:
{"mode":"PLAN | RETURN | REFUSE | HUMAN","content":"string","confidence":0.0,"reason":"string","normalized_goal":null,"metadata":{}}

Rules:
- Greetings, chat, conceptual questions, and explanation requests use RETURN.
- Requests to run, deploy, test, inspect an environment, call tools, or produce artifacts use PLAN.
- Destructive, unauthorized, or unsafe requests use REFUSE.
- Tasks requiring manual approval, login, permission, or confirmation use HUMAN.
- PLAN requires a concise, non-empty normalized_goal.
- RETURN, REFUSE, and HUMAN require non-empty content.
- Do not invent credentials, URLs, versions, file paths, or environment details.
- raw_user_input is the source of truth.

Input context:
""" + "\n".join(context_lines)
