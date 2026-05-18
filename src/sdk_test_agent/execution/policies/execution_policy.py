from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExecutionPolicy:
    """Small v1 execution policy holder reserved for future interpreter controls."""

    stop_on_unsupported_step: bool = True
    persist_final_summary: bool = True
