from __future__ import annotations

from typing import Any

from .llm_config import LlmModelConfig, LlmProviderConfig, LlmRouteConfig
from .model_registry import ModelRegistry


def load_registry_from_dict(data: dict[str, Any]) -> ModelRegistry:
    llm = data.get("llm", data)
    registry = ModelRegistry()
    for name, raw in llm.get("providers", {}).items():
        registry.register_provider(LlmProviderConfig(provider_name=name, **raw))
    for alias, raw in llm.get("models", {}).items():
        registry.register_model(LlmModelConfig(alias=alias, **raw))
    for name, raw in llm.get("routing", {}).items():
        registry.register_route(LlmRouteConfig(route_name=name, **raw))
    return registry
