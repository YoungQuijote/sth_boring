from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from .llm_models import LlmRequest, LlmResponse
from .streaming.stream_models import LlmStreamEvent


class LlmClientProtocol(Protocol):
    def complete(self, request: LlmRequest) -> LlmResponse:
        ...

    async def acomplete(self, request: LlmRequest) -> LlmResponse:
        ...

    async def astream(self, request: LlmRequest) -> AsyncIterator[LlmStreamEvent]:
        ...
