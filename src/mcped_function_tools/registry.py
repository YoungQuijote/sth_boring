from __future__ import annotations

from collections.abc import Iterable

from .types import ToolResult, ToolSpec


class ToolRegistry:
    """In-memory tool registry with validation and normalized execution."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' is already registered")
        self._tools[spec.name] = spec

    def list_tools(self, *, tag: str | None = None) -> list[ToolSpec]:
        tools: Iterable[ToolSpec] = self._tools.values()
        if tag:
            tools = [tool for tool in tools if tag in tool.tags]
        return sorted(tools, key=lambda t: t.name)

    def to_openai_function_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self.list_tools()
        ]

    def call(self, name: str, args: dict) -> ToolResult:
        if name not in self._tools:
            return ToolResult(ok=False, content=None, error=f"Unknown tool '{name}'")

        try:
            value = self._tools[name].handler(args)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, content=None, error=str(exc))

        return ToolResult(ok=True, content=value)
