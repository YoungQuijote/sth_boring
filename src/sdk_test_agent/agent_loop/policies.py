from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LoopPolicy:
    max_iterations: int = 3
    fail_on_validation_error: bool = True
    fail_on_preflight_error: bool = True
    allow_human_interrupt: bool = False
    allow_ask_input: bool = True
    task_check_min_confidence: float = 0.5
