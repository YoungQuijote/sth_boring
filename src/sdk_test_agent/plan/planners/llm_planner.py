from __future__ import annotations

import json
from dataclasses import asdict

from sdk_test_agent.llm.llm_models import LlmMessage, LlmRequest
from sdk_test_agent.llm.llm_provider_base import LlmClientProtocol
from sdk_test_agent.plan.plan_context import PlannerInput
from sdk_test_agent.plan.plan_enums import PlannerKind
from sdk_test_agent.plan.plan_errors import PlanLlmClientNotConfiguredError, PlanLlmOutputError
from sdk_test_agent.plan.plan_models import ExecutionPlanDraft, PlanStep


class LlmPlanner:
    name = "llm_planner"
    version = "0.1.0"
    kind = PlannerKind.LLM

    def __init__(self, llm_client: LlmClientProtocol | None = None, model: str = "planner-model") -> None:
        self.llm_client = llm_client
        self.model = model

    def plan(self, planner_input: PlannerInput) -> ExecutionPlanDraft:
        if self.llm_client is None:
            raise PlanLlmClientNotConfiguredError("LlmPlanner requires an llm_client")

        prompt = self._build_prompt(planner_input)
        response = self.llm_client.complete(
            LlmRequest(
                model=self.model,
                messages=[LlmMessage(role="user", content=prompt)],
                temperature=0.0,
                response_format="json_object",
                metadata={"planner": self.name},
            )
        )
        return self._parse_response(response.content, planner_input)

    def _build_prompt(self, planner_input: PlannerInput) -> str:
        ctx = planner_input.base_context
        llm = planner_input.llm_context
        parts = [
            llm.system_prompt if llm and llm.system_prompt else "You are SdkTestAgent planner. Output JSON only.",
            llm.output_schema_prompt if llm and llm.output_schema_prompt else "Return plan_summary, steps, assumptions, missing_information, risk_notes.",
            "Base context:",
            json.dumps(asdict(ctx), default=str, sort_keys=True),
        ]
        if llm:
            parts.append(f"User instruction: {llm.user_instruction_raw}")
            if llm.system_constraints_text:
                parts.append(f"Constraints: {llm.system_constraints_text}")
            for skill in llm.skills:
                parts.append(f"Skill {skill.name}:\n{skill.content}")
            for memory in llm.retrieved_plan_memories:
                parts.append(f"Retrieved plan memory {memory.memory_id}: {json.dumps(memory.plan_json, default=str)}")
        return "\n\n".join(parts)

    def _parse_response(self, content: str, planner_input: PlannerInput) -> ExecutionPlanDraft:
        try:
            raw = json.loads(content)
            steps = [PlanStep(**step) for step in raw.get("steps", [])]
        except Exception as exc:  # noqa: BLE001
            raise PlanLlmOutputError(f"failed to parse LLM plan JSON: {exc}") from exc

        ctx = planner_input.base_context
        return ExecutionPlanDraft(
            task_id=ctx.task_id,
            task_type=ctx.task_type,
            goal=ctx.goal,
            planner_name=self.name,
            planner_version=self.version,
            plan_summary=raw.get("plan_summary", ""),
            steps=steps,
            assumptions=raw.get("assumptions", []),
            missing_information=raw.get("missing_information", []),
            risk_notes=raw.get("risk_notes", []),
            raw_llm_output=content,
            metadata=raw.get("metadata", {}),
        )
