from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    pass


class InspectionStatus(_StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class FindingLevel(_StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class InspectionSubjectType(_StrEnum):
    PACKAGE = "package"
    ENVIRONMENT = "environment"
