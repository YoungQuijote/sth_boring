from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .llm_config import LlmModelConfig, LlmProviderConfig, LlmRouteConfig
from .llm_errors import LlmModelNotFoundError, LlmProviderNotFoundError


@dataclass(slots=True)
class ResolvedLlmTarget:
    provider_config: LlmProviderConfig
    model_config: LlmModelConfig
    model: str
    api_protocol: str
    request_defaults: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LlmProviderConfig] = {}
        self._models: dict[str, LlmModelConfig] = {}
        self._routes: dict[str, LlmRouteConfig] = {}

    def register_provider(self, config: LlmProviderConfig) -> None:
        self._providers[config.provider_name] = config

    def register_model(self, config: LlmModelConfig) -> None:
        self._models[config.alias] = config

    def register_route(self, config: LlmRouteConfig) -> None:
        self._routes[config.route_name] = config

    def get_provider(self, provider_name: str) -> LlmProviderConfig:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise LlmProviderNotFoundError(f"provider not found: {provider_name}") from exc

    def get_model(self, alias: str) -> LlmModelConfig:
        try:
            return self._models[alias]
        except KeyError as exc:
            raise LlmModelNotFoundError(f"model alias not found: {alias}") from exc

    def get_route(self, route_name: str) -> LlmRouteConfig | None:
        return self._routes.get(route_name)

    def resolve(self, model_alias: str) -> ResolvedLlmTarget:
        model_config = self.get_model(model_alias)
        provider_config = self.get_provider(model_config.provider_name)
        defaults: dict[str, Any] = {
            "temperature": model_config.temperature,
            "top_p": model_config.top_p,
            "max_output_tokens": model_config.max_output_tokens,
            "reasoning_effort": model_config.reasoning_effort,
        }
        if model_config.default_response_format is not None:
            defaults["response_format"] = model_config.default_response_format.response_format
            defaults["json_schema"] = model_config.default_response_format.json_schema
            defaults["strict_json_schema"] = model_config.default_response_format.strict
        return ResolvedLlmTarget(
            provider_config=provider_config,
            model_config=model_config,
            model=model_config.model,
            api_protocol=model_config.api_protocol,
            request_defaults={k: v for k, v in defaults.items() if v is not None},
        )
