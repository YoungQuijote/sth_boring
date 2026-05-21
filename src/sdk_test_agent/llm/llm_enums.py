from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    pass


class LlmProviderType(_StrEnum):
    FAKE = "fake"
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    VLLM = "vllm"
    UNKNOWN = "unknown"


class LlmApiProtocol(_StrEnum):
    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"


class LlmMessageRole(_StrEnum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LlmResponseFormatType(_StrEnum):
    TEXT = "text"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"


class LlmFinishReason(_StrEnum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    UNKNOWN = "unknown"


class LlmStreamEventType(_StrEnum):
    TEXT_DELTA = "text_delta"
    JSON_DELTA = "json_delta"
    TOOL_CALL_DELTA = "tool_call_delta"
    MESSAGE_DONE = "message_done"
    RESPONSE_DONE = "response_done"
    ERROR = "error"
