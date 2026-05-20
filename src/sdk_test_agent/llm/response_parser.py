from __future__ import annotations

import json
from typing import Any

from .llm_errors import LlmResponseParseError
from .llm_models import LlmResponse


class LlmJsonResponseParser:
    def parse_json_object(self, response: LlmResponse) -> dict[str, Any]:
        if response.parsed_json is not None:
            return response.parsed_json
        try:
            value = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise LlmResponseParseError(f"failed to parse LLM response as JSON object: {exc}") from exc
        if not isinstance(value, dict):
            raise LlmResponseParseError("LLM response is not a JSON object")
        return value
