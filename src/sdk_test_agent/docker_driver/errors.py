class DockerDriverError(Exception):
    """Base docker driver error."""


class DockerConnectionError(DockerDriverError):
    """Raised when docker daemon connection fails."""


class DockerImageError(DockerDriverError):
    """Raised for image pull/inspect failures."""


class DockerContainerError(DockerDriverError):
    """Raised for container lifecycle failures."""


class DockerExecError(DockerDriverError):
    """Raised when exec fails."""


class DockerArchiveError(DockerDriverError):
    """Raised for archive put/get failures."""
