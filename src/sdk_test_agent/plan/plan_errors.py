class PlanError(Exception):
    """Base plan module error."""


class PlanValidationError(PlanError):
    """Raised when a plan cannot pass validation."""


class PlanLlmClientNotConfiguredError(PlanError):
    """Raised when LLM planner has no configured client."""


class PlanLlmOutputError(PlanError):
    """Raised when LLM output cannot be parsed into a plan draft."""
