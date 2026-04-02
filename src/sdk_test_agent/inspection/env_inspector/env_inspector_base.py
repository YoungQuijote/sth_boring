from __future__ import annotations

from abc import ABC, abstractmethod

from .env_inspector_models import DockerEnvInspectionInput, EnvInspectionReport


class BaseEnvInspector(ABC):
    inspector_name: str

    @abstractmethod
    def inspect_docker_env(self, data: DockerEnvInspectionInput) -> EnvInspectionReport:
        raise NotImplementedError
