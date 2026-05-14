from __future__ import annotations

RUNTIME_DB_NAME = "runtime_registry.db"


class EngineConnectionMode:
    LOCAL = "local"
    TCP = "tcp"
    SSH = "ssh"


class EngineHealthStatus:
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNREACHABLE = "unreachable"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class ImageSourceType:
    PULLED = "pulled"
    BUILT = "built"
    LOADED = "loaded"
    COMMITTED = "committed"
    UNKNOWN = "unknown"
