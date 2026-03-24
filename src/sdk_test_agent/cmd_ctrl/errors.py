class CommandControlError(Exception):
    """Base command-control error."""


class ActionDispatchError(CommandControlError):
    """Raised when action route is missing."""


class OperatorExecutionError(CommandControlError):
    """Raised when operator execution fails."""


class PolicyViolationError(CommandControlError):
    """Raised when request violates policies."""


class GuardDeniedError(CommandControlError):
    """Raised when guarded execution is denied by policy."""


class GuardEscalationRequired(CommandControlError):
    """Raised when guarded execution should escalate to HITL or upper workflow."""
