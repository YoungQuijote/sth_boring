from __future__ import annotations

from .stream_models import LlmStreamEvent


class StreamEventParser:
    """Placeholder parser for future provider-specific streaming adapters."""

    def parse_event(self, raw_event) -> LlmStreamEvent:
        return LlmStreamEvent(event_type="response_done", raw=raw_event)
