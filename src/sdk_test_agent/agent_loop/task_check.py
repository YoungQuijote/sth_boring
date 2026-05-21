from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from sdk_test_agent.llm.llm_models import LlmMessage, LlmRequest
from sdk_test_agent.llm.response_parser import LlmJsonResponseParser

LoopLevel = Literal["satisfied", "need_replan", "failed", "need_input", "need_human", "blocked"]
RouteType = Literal["end", "replan", "fail", "ask_input", "human_interrupt"]


@dataclass(slots=True)
class TaskCheckRequest:
    task_id: str
    task_type: str
    user_goal: str
    iteration: int
    plan: dict[str, Any] | None = None
    execution_result: dict[str, Any] | None = None
    capability_snapshot_id: str | None = None
    capability_digest: str | None = None
    previous_attempts: list[dict[str, Any]] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskCheckDecision:
    loop_level: LoopLevel
    route: RouteType
    confidence: float
    reason: str
    evidence_refs: list[str] = field(default_factory=list)
    evidence_summary: str | None = None
    replan_hint: str | None = None
    input_request: str | None = None
    human_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_level": self.loop_level,
            "route": self.route,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "evidence_summary": self.evidence_summary,
            "replan_hint": self.replan_hint,
            "input_request": self.input_request,
            "human_message": self.human_message,
            "metadata": dict(self.metadata),
        }


class TaskChecker(Protocol):
    def check(self, request: TaskCheckRequest) -> TaskCheckDecision:
        ...


class LlmTaskChecker:
    def __init__(self, llm_client, model: str | None = None, model_alias: str | None = None, api_protocol: str | None = None) -> None:
        self.llm_client = llm_client
        self.model = model or "task-check-model"
        self.model_alias = model_alias
        self.api_protocol = api_protocol
        self.parser = LlmJsonResponseParser()

    def check(self, request: TaskCheckRequest) -> TaskCheckDecision:
        prompt = self._build_prompt(request)
        response = self.llm_client.complete(
            LlmRequest(
                model_alias=self.model_alias,
                model=None if self.model_alias else self.model,
                api_protocol=self.api_protocol,
                messages=[LlmMessage(role="user", content=prompt)],
                response_format="json_object",
                temperature=0.0,
                metadata={"checker": "llm_task_checker"},
            )
        )
        try:
            payload = self.parser.parse_json_object(response)
            return self._from_payload(payload)
        except Exception:
            return TaskCheckDecision(loop_level="need_replan", route="replan", confidence=0.0, reason="task checker failed to parse decision")

    def _build_prompt(self, request: TaskCheckRequest) -> str:
        return (
            "Return strict JSON with loop_level, route, confidence, reason.\n"
            "Allowed loop_level: satisfied, need_replan, failed, need_input, need_human, blocked.\n"
            "Allowed route: end, replan, fail, ask_input, human_interrupt.\n"
            f"Request:\n{json.dumps(request.__dict__, ensure_ascii=False, sort_keys=True, default=str)}"
        )

    @staticmethod
    def _from_payload(payload: dict[str, Any]) -> TaskCheckDecision:
        return TaskCheckDecision(
            loop_level=payload.get("loop_level", "need_replan"),
            route=payload.get("route", "replan"),
            confidence=float(payload.get("confidence", 0.0)),
            reason=str(payload.get("reason", "")),
            evidence_refs=list(payload.get("evidence_refs", [])),
            evidence_summary=payload.get("evidence_summary"),
            replan_hint=payload.get("replan_hint"),
            input_request=payload.get("input_request"),
            human_message=payload.get("human_message"),
            metadata=dict(payload.get("metadata", {})),
        )
