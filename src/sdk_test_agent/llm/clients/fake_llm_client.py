from __future__ import annotations

from collections.abc import AsyncIterator

from sdk_test_agent.llm.llm_enums import LlmProviderType
from sdk_test_agent.llm.llm_models import LlmRequest, LlmResponse
from sdk_test_agent.llm.streaming.stream_models import LlmStreamEvent


class FakeLlmClient:
    def __init__(
        self,
        response_content: str = "",
        *,
        response: LlmResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response_content = response_content
        self.response = response
        self.error = error
        self.requests: list[LlmRequest] = []

    def complete(self, request: LlmRequest) -> LlmResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.response is not None:
            return self.response
        return LlmResponse(
            content=self.response_content,
            model=request.model,
            model_alias=request.model_alias,
            provider_name=LlmProviderType.FAKE,
            provider_type=LlmProviderType.FAKE,
        )

    async def acomplete(self, request: LlmRequest) -> LlmResponse:
        return self.complete(request)

    async def astream(self, request: LlmRequest) -> AsyncIterator[LlmStreamEvent]:
        response = self.complete(request)
        yield LlmStreamEvent(event_type="response_done", content=response.content, raw=response.raw)
