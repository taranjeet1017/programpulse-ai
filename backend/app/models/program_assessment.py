"""Complete assessment contract with resolvable evidence identifiers."""
from datetime import date
from typing import Literal

from pydantic import Field

from app.models.assessment import AssessmentModel, Confidence, HealthStatus
from app.models.extraction import ExtractionUsage
from app.models.normalized_evidence import Dimension, EvidenceGroup, NormalizedEvidence


class ProgramPulseHealth(AssessmentModel):
    overall_status: HealthStatus
    confidence: Confidence
    status_conflict: bool
    leadership_attention_required: bool


class ReasonDetail(AssessmentModel):
    reason: str
    supporting_evidence_ids: list[str] = Field(min_length=1)


class DimensionAssessment(AssessmentModel):
    status: HealthStatus
    reasons: list[str]
    reason_details: list[ReasonDetail] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(min_length=1)


class ChallengeProvenance(AssessmentModel):
    challenge_id: str
    reported_claim: str
    reported_source: str
    claim_evidence_ids: list[str]
    supporting_evidence_ids: list[str]
    reason: str
    severity: Literal["AMBER", "RED"]
    assessment: Literal["CHALLENGED", "REQUIRES_VALIDATION"]
    leadership_relevance: str


class GovernanceChallenge(AssessmentModel):
    challenge_id: str
    reported_claim: str
    reported_source: str
    claim_evidence_ids: list[str]
    assessment: Literal["CHALLENGED", "REQUIRES_VALIDATION"]
    reason: str
    severity: Literal["AMBER", "RED"]
    supporting_evidence_ids: list[str] = Field(min_length=1)
    leadership_relevance: str
    conflict_key: str | None = None
    provenance: list[ChallengeProvenance] = Field(default_factory=list)


class RecommendedAction(AssessmentModel):
    action_id: str
    description: str
    supporting_evidence_ids: list[str] = Field(min_length=1)


class ProgramAssessment(AssessmentModel):
    project: str
    assessment_date: date = Field(description="Evidence reporting date, not the request execution date.")
    assessment_version: Literal["1.0"] = "1.0"
    reported_health: HealthStatus
    programpulse_assessment: ProgramPulseHealth
    health_dimensions: dict[Dimension, DimensionAssessment]
    evidence_catalog: list[NormalizedEvidence]
    key_evidence_ids: list[str]
    # Keep the original full-catalog alias temporarily for existing API clients.
    key_evidence: list[NormalizedEvidence] = Field(
        json_schema_extra={"deprecated": True},
        description="Deprecated full-catalog alias. Use evidence_catalog and key_evidence_ids."
    )
    evidence_groups: list[EvidenceGroup]
    governance_challenges: list[GovernanceChallenge]
    recommended_actions: list[RecommendedAction]
    executive_summary: str
    reported_health_source: str
    usage: ExtractionUsage


class DimensionSummary(AssessmentModel):
    dimension: Dimension
    status: HealthStatus
    headline_reason: str
    evidence_count: int


class KeyEvidenceSummary(AssessmentModel):
    evidence_id: str
    description: str
    dimensions: list[Dimension]
    evidence_kind: str
    source_type: str
    source_name: str
    source_reference: str
    source_section: str | None
    source_snippet: str | None


class DashboardChallenge(AssessmentModel):
    challenge_id: str
    reported_claim: str
    assessment: Literal["CHALLENGED", "REQUIRES_VALIDATION"]
    reason: str
    severity: Literal["AMBER", "RED"]
    supporting_evidence_ids: list[str]
    claim_evidence_ids: list[str]


class DashboardAssessment(AssessmentModel):
    project: str
    assessment_date: date
    assessment_version: str
    reported_health: HealthStatus
    programpulse_health: HealthStatus
    status_conflict: bool
    confidence: Confidence
    leadership_attention_required: bool
    dimension_summary: list[DimensionSummary]
    top_governance_challenges: list[DashboardChallenge]
    top_recommended_actions: list[RecommendedAction]
    executive_summary: str
    key_evidence: list[KeyEvidenceSummary]
