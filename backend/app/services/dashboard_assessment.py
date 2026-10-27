"""Pure projections of a completed assessment; this module never calls AI."""
from app.models.assessment import HealthStatus
from app.models.normalized_evidence import Dimension, NormalizedEvidence
from app.models.program_assessment import (
    DashboardAssessment, DashboardChallenge, DimensionSummary, KeyEvidenceSummary,
    ProgramAssessment, DimensionAssessment, GovernanceChallenge, RecommendedAction,
)

KEY_EVIDENCE_LIMIT = 8
TOP_CHALLENGES_LIMIT = 5
TOP_ACTIONS_LIMIT = 5


def select_key_evidence(
    dimensions: dict[Dimension, DimensionAssessment], challenges: list[GovernanceChallenge],
    actions: list[RecommendedAction], catalog: list[NormalizedEvidence],
) -> list[str]:
    scores: dict[str, int] = {}
    for dimension in dimensions.values():
        if dimension.status == HealthStatus.GREEN:
            continue
        for identifier in dimension.supporting_evidence_ids:
            scores[identifier] = scores.get(identifier, 0) + (100 if dimension.status == HealthStatus.RED else 30)
    for challenge in challenges:
        for identifier in set(challenge.supporting_evidence_ids + challenge.claim_evidence_ids):
            scores[identifier] = scores.get(identifier, 0) + 10
    for action in actions:
        for identifier in action.supporting_evidence_ids:
            scores[identifier] = scores.get(identifier, 0) + 5
    eligible = {item.evidence_id for item in catalog if item.category != "raid_snapshot"}
    ranked = sorted(eligible & scores.keys(), key=lambda identifier: (-scores[identifier], identifier))
    selected = []
    # Give each adverse dimension a representative before filling the shortlist.
    for dimension in sorted(dimensions.values(), key=lambda d: d.status != HealthStatus.RED):
        if dimension.status == HealthStatus.GREEN:
            continue
        best = next((identifier for identifier in ranked if identifier in dimension.supporting_evidence_ids), None)
        if best is not None and best not in selected:
            selected.append(best)
    selected.extend(identifier for identifier in ranked if identifier not in selected)
    return selected[:KEY_EVIDENCE_LIMIT]


def summarize_assessment(completed: ProgramAssessment) -> DashboardAssessment:
    """Reuse a completed result; callers must not rerun extraction for projection."""
    by_id = {item.evidence_id: item for item in completed.evidence_catalog}
    health = completed.programpulse_assessment
    return DashboardAssessment(
        project=completed.project, assessment_date=completed.assessment_date,
        assessment_version=completed.assessment_version, reported_health=completed.reported_health,
        programpulse_health=health.overall_status, status_conflict=health.status_conflict,
        confidence=health.confidence, leadership_attention_required=health.leadership_attention_required,
        dimension_summary=[DimensionSummary(
            dimension=name, status=result.status,
            headline_reason=result.reason_details[0].reason if result.reason_details else result.reasons[0],
            evidence_count=len(set(result.supporting_evidence_ids)),
        ) for name, result in completed.health_dimensions.items()],
        top_governance_challenges=[DashboardChallenge.model_validate(item.model_dump(include={
            "challenge_id", "reported_claim", "assessment", "reason", "severity",
            "supporting_evidence_ids", "claim_evidence_ids",
        })) for item in completed.governance_challenges[:TOP_CHALLENGES_LIMIT]],
        top_recommended_actions=completed.recommended_actions[:TOP_ACTIONS_LIMIT],
        executive_summary=completed.executive_summary,
        key_evidence=[KeyEvidenceSummary.model_validate(by_id[identifier].model_dump(include={
            "evidence_id", "description", "dimensions", "evidence_kind", "source_type", "source_name",
            "source_reference", "source_section", "source_snippet",
        })) for identifier in completed.key_evidence_ids],
    )
