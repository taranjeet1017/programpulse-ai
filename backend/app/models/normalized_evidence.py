"""Canonical evidence and provenance independent of its producer."""
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import Field, JsonValue

from app.models.assessment import AssessmentModel, Confidence


class Dimension(StrEnum):
    SCHEDULE = "SCHEDULE"
    SCOPE = "SCOPE"
    QUALITY = "QUALITY"
    DEPENDENCIES = "DEPENDENCIES"
    ACTIONS = "ACTIONS"
    GOVERNANCE = "GOVERNANCE"


class SourceType(StrEnum):
    AI_STATUS_REPORT = "AI_STATUS_REPORT"
    RAID_LOG = "RAID_LOG"
    MILESTONE_PLAN = "MILESTONE_PLAN"
    QUALITY_DATA = "QUALITY_DATA"


class NormalizedEvidence(AssessmentModel):
    evidence_id: str
    evidence_key: str | None = None
    project_id: str
    category: str
    dimensions: list[Dimension]
    description: str
    evidence_kind: Literal["reported_claim", "reported_observation", "missing_information", "contradiction", "operational_record"]
    severity: str | None = None
    owner: str | None = None
    due_date: date | None = None
    status: str | None = None
    impact: str | None = None
    source_type: SourceType
    source_name: str
    source_section: str | None = None
    source_snippet: str | None = None
    source_reference: str
    extraction_confidence: Confidence | None = None
    is_overdue: bool | None = None
    is_critical: bool | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class EvidenceGroup(AssessmentModel):
    group_id: str
    evidence_key: str | None
    evidence_ids: list[str]
    dimensions: list[Dimension]


class ConsolidatedEvidence(AssessmentModel):
    evidence: list[NormalizedEvidence]
    groups: list[EvidenceGroup]
