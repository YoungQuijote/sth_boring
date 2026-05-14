class LlmError(Exception):
    """Base LLM infrastructure error."""


class LlmConfigError(LlmError):
    """Raised for invalid provider/model/route configuration."""


class LlmProviderNotFoundError(LlmConfigError):
    """Raised when provider config is missing."""


class LlmModelNotFoundError(LlmConfigError):
    """Raised when model alias config is missing."""


class LlmCapabilityError(LlmError):
    """Raised when a request requires unsupported model/provider capability."""


class LlmProviderError(LlmError):
    """Raised for provider SDK/API failures."""


class LlmTimeoutError(LlmProviderError):
    """Raised for provider timeout failures."""


class LlmRateLimitError(LlmProviderError):
    """Raised for provider rate limits."""


class LlmAuthenticationError(LlmProviderError):
    """Raised for provider authentication failures."""


class LlmResponseParseError(LlmError):
    """Raised when LLM response cannot be parsed as requested."""
