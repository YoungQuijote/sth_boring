from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanContextBase:
    task_id: str
    task_type: str
    goal: str
    package_report: Any | None = None
    env_report: Any | None = None
    text_parse_result: Any | None = None
    runtime_target: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    available_capabilities: list[str] = field(default_factory=list)
    prior_artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillRef:
    skill_id: str
    name: str
    version: str | None = None
    path: str | None = None
    summary: str | None = None


@dataclass(slots=True)
class PlanningSkill:
    skill_id: str
    name: str
    content: str
    version: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RetrievedPlanMemory:
    memory_id: str
    task_type: str
    similarity: float
    plan_summary: str
    plan_json: dict[str, Any]
    success_score: float | None = None
    source_task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmPlanningContext:
    user_instruction_raw: str
    system_prompt: str | None = None
    output_schema_prompt: str | None = None
    skills: list[PlanningSkill] = field(default_factory=list)
    skill_refs: list[SkillRef] = field(default_factory=list)
    fewshot_examples: list[str] = field(default_factory=list)
    retrieved_plan_memories: list[RetrievedPlanMemory] = field(default_factory=list)
    system_constraints_text: str | None = None
    extra_prompt_vars: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlannerInput:
    base_context: PlanContextBase
    llm_context: LlmPlanningContext | None = None
    planner_options: dict[str, Any] = field(default_factory=dict)
