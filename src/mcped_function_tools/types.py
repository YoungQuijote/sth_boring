from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class ToolSpec:
    """Tool description for agent runtimes and MCP-style adapters."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolResult:
    """Normalized execution result with structured metadata."""

    ok: bool
    content: Any
    error: str | None = None
