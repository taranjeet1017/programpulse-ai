"""Build deterministic, traceable output from the rules result."""
from datetime import date

from app.models.assessment import Assessment, HealthStatus
from app.models.extraction import ExtractionUsage
from app.models.normalized_evidence import ConsolidatedEvidence, Dimension
from app.models.program_assessment import DimensionAssessment, ProgramAssessment, ProgramPulseHealth, ReasonDetail
from app.services.governance_challenges import generate_actions, generate_challenges
from app.services.dashboard_assessment import select_key_evidence


def build_assessment(assessment: Assessment, evidence: ConsolidatedEvidence, usage: ExtractionUsage,
                     assessment_date: date | None = None) -> ProgramAssessment:
    dimensions = {}
    for dimension in Dimension:
        findings = [item for item in assessment.evidence if item.dimension == dimension.value.lower()]
        dimensions[dimension] = DimensionAssessment(
            status=getattr(assessment.health_dimensions, dimension.value.lower()),
            reasons=[item.description for item in findings],
            reason_details=[ReasonDetail(reason=item.description,
                supporting_evidence_ids=sorted(set(item.references))) for item in findings],
            supporting_evidence_ids=sorted({identifier for item in findings for identifier in item.references}),
        )
    actions = generate_actions(assessment)
    challenges = generate_challenges(assessment, evidence)
    pressures = []
    dependency = next((item for item in evidence.evidence if item.category == "dependency"
                       and item.is_critical and item.is_overdue), None)
    if dimensions[Dimension.DEPENDENCIES].status != HealthStatus.GREEN:
        pressures.append(f"a critical overdue dependency ({dependency.description})" if dependency else "dependency exposure")
    if dimensions[Dimension.QUALITY].status != HealthStatus.GREEN:
        pressures.append("quality remediation")
    if dimensions[Dimension.SCHEDULE].status != HealthStatus.GREEN:
        pressures.append("critical-path delays")
    if not pressures:
        pressures = [f"{name.value.lower()} exposure" for name, result in dimensions.items()
                     if result.status != HealthStatus.GREEN]
    next_steps = []
    if dimensions[Dimension.DEPENDENCIES].status != HealthStatus.GREEN:
        next_steps.append("secure recovery commitments")
    if dimensions[Dimension.SCHEDULE].status != HealthStatus.GREEN:
        next_steps.append("validate UAT readiness")
    if not next_steps and actions:
        next_steps.append(actions[0].description.rstrip(".").lower())
    summary = (f"{assessment.project}: reported {assessment.reported_health.value}, "
               f"evidenced {assessment.assessed_health.value} by ProgramPulse. "
               + ((", ".join(pressures).capitalize() + (" create" if len(pressures) > 1 else " creates") + " material delivery exposure. ") if pressures else "")
               + ("Leadership attention is required to " + " and ".join(next_steps) + "."
                  if next_steps else "No rule-triggered leadership intervention is required."))
    if assessment_date is None:
        # Older internal callers can obtain the same as-of date from the snapshot.
        quality = next(item for item in evidence.evidence if item.category == "quality_snapshot")
        assessment_date = date.fromisoformat(quality.metadata["record"]["reporting_date"])
    key_ids = select_key_evidence(dimensions, challenges, actions, evidence.evidence)
    return ProgramAssessment(
        project=assessment.project, assessment_date=assessment_date, reported_health=assessment.reported_health,
        programpulse_assessment=ProgramPulseHealth(
            overall_status=assessment.assessed_health, confidence=assessment.confidence,
            status_conflict=assessment.status_conflict,
            leadership_attention_required=assessment.leadership_attention_required),
        health_dimensions=dimensions, evidence_catalog=evidence.evidence,
        key_evidence_ids=key_ids, key_evidence=evidence.evidence, evidence_groups=evidence.groups,
        governance_challenges=challenges, recommended_actions=actions, executive_summary=summary,
        reported_health_source="weekly_status_report.md#Reported overall health", usage=usage,
    )
