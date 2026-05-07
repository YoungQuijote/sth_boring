from __future__ import annotations

from typing import Protocol

from .llm_models import LlmRequest, LlmResponse


class LlmClientProtocol(Protocol):
    def complete(self, request: LlmRequest) -> LlmResponse:
        ...
