from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EnvFingerprintInput:
    runtime: str
    engine_id: str
    image_id: str
    sdk_name: str
    sdk_version: str | None
    command: list[str]
    env: dict[str, str]
    ports: list[str]
