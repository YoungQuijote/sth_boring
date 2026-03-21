from __future__ import annotations

from .registry import ToolRegistry


class MCPFunctionAdapter:
    """Small adapter layer that exposes registry actions as MCP-like methods."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def list_tools(self) -> dict:
        return {
            "tools": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "inputSchema": spec.input_schema,
                }
                for spec in self.registry.list_tools()
            ]
        }

    def call_tool(self, name: str, arguments: dict) -> dict:
        result = self.registry.call(name, arguments)
        if result.ok:
            return {"isError": False, "content": [{"type": "json", "json": result.content}]}

        return {"isError": True, "content": [{"type": "text", "text": result.error or "Unknown error"}]}
