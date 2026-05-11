class SandboxError(Exception):
    """Base sandbox error."""


class SandboxNotReadyError(SandboxError):
    """Raised when an action requires a ready/running sandbox."""


class SandboxStateError(SandboxError):
    """Raised when sandbox state transition is invalid."""


class SandboxExecError(SandboxError):
    """Raised when exec-level operations fail."""


class SandboxArtifactError(SandboxError):
    """Raised for artifact encode/decode failures."""
