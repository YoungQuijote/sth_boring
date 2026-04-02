from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .inspection_enums import FindingLevel, InspectionStatus, InspectionSubjectType


@dataclass(slots=True)
class InspectionEvidence:
    source: str
    ref: str | None = None
    snippet: str | None = None


@dataclass(slots=True)
class InspectionFinding:
    code: str
    level: FindingLevel
    summary: str
    detail: str | None = None
    evidence: list[InspectionEvidence] = field(default_factory=list)


@dataclass(slots=True)
class InspectionReportBase:
    subject_type: InspectionSubjectType
    subject_name: str | None
    status: InspectionStatus
    findings: list[InspectionFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
