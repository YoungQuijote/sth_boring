from __future__ import annotations

from .llm_config import LlmModelConfig


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, LlmModelConfig] = {}

    def register(self, name: str, config: LlmModelConfig) -> None:
        self._models[name] = config

    def get(self, name: str) -> LlmModelConfig | None:
        return self._models.get(name)
