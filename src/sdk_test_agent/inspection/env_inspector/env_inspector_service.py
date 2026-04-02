from __future__ import annotations

from .env_inspector_base import BaseEnvInspector
from .env_inspector_models import DockerEnvInspectionInput, EnvInspectionReport


class EnvInspectorService:
    def __init__(self, docker_env_inspector: BaseEnvInspector) -> None:
        self.docker_env_inspector = docker_env_inspector

    def inspect_docker_env(self, data: DockerEnvInspectionInput) -> EnvInspectionReport:
        return self.docker_env_inspector.inspect_docker_env(data)
