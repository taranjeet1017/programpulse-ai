"""Structured extraction contracts; no calculated-health field exists here."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.assessment import Confidence, HealthStatus

MAX_REPORT_CHARACTERS = 100_000
OBSERVATION_FIELDS = (
    "delivery_claims", "risks", "dependencies", "quality_signals",
    "schedule_signals", "scope_changes", "actions", "governance_statements",
    "statements_requiring_validation",
)


class ExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedObservation(ExtractionModel):
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_kind: Literal["reported_claim", "reported_observation", "missing_information", "contradiction"]
    severity_hint: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None
    owner: str | None
    due_date: date | None
    status: str | None
    source_section: str | None
    source_snippet: str = Field(min_length=1, description="Contiguous verbatim excerpt from the submitted report.")
    impact: str | None
    confidence: Confidence | None = Field(
        description="Extraction confidence: how strongly the source supports this representation. "
                    "HIGH does not mean the reported claim is true or independently verified."
    )
    evidence_key: str | None = Field(
        default=None, min_length=1,
        description="Optional stable event key shared across categories for the same underlying event."
    )

    @field_validator("due_date")
    @classmethod
    def sane_due_year(cls, value: date | None) -> date | None:
        # Preserve usable evidence even when the model invents a distant year.
        return value if value is None or 1900 <= value.year <= 2100 else None


class StatusReportExtraction(ExtractionModel):
    # Structured Outputs requires keys; nullable values represent absent facts.
    project_name: str | None
    reporting_date: date | None
    reported_health: HealthStatus | None
    reported_release_date: date | None
    delivery_claims: list[ExtractedObservation]
    risks: list[ExtractedObservation]
    dependencies: list[ExtractedObservation]
    quality_signals: list[ExtractedObservation]
    schedule_signals: list[ExtractedObservation]
    scope_changes: list[ExtractedObservation]
    actions: list[ExtractedObservation]
    governance_statements: list[ExtractedObservation]
    statements_requiring_validation: list[ExtractedObservation]


    @field_validator("reporting_date", "reported_release_date")
    @classmethod
    def sane_metadata_year(cls, value: date | None) -> date | None:
        if value is not None and not 1900 <= value.year <= 2100:
            raise ValueError("Project date year must be between 1900 and 2100")
        return value


class StatusReportRequest(ExtractionModel):
    text: str = Field(min_length=1, max_length=MAX_REPORT_CHARACTERS)

    @field_validator("text")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Report text must not be blank")
        return value


class ExtractionUsage(ExtractionModel):
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ExtractionResult(ExtractionModel):
    extraction: StatusReportExtraction
    usage: ExtractionUsage
