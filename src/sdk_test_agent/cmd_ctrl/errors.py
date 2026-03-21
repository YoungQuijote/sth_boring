class CommandControlError(Exception):
    """Base command-control error."""


class ActionDispatchError(CommandControlError):
    """Raised when action route is missing."""


class OperatorExecutionError(CommandControlError):
    """Raised when operator execution fails."""


class PolicyViolationError(CommandControlError):
    """Raised when request violates policies."""
