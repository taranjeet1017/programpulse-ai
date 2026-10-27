"""Deterministic rules, evaluated as of the evidence reporting date."""
from app.models.assessment import (
    Assessment, Confidence, Evidence, HealthDimensions, HealthStatus, LeadershipAction,
)
from app.models.input_evidence import ProjectEvidence, WeeklyStatusReport
from app.models.normalized_evidence import NormalizedEvidence

MATERIAL_SLIPPAGE_DAYS = 3
SIGNIFICANT_SEV2_COUNT = 5


def _calculate_operational_assessment(bundle: ProjectEvidence) -> Assessment:
    report = bundle.weekly_status
    quality = bundle.quality
    raid_refs = {item.id: f"raid_log.json#/items/{index}" for index, item in enumerate(bundle.raid.items)}
    active = [item for item in bundle.raid.items if item.status == "OPEN"]
    dimensions = HealthDimensions(**{name: HealthStatus.GREEN for name in HealthDimensions.model_fields})
    evidence: list[Evidence] = []

    def record(dimension: str, rating: HealthStatus, description: str, references: list[str]) -> None:
        setattr(dimensions, dimension, rating)
        evidence.append(Evidence(dimension=dimension, description=description, references=references))

    for item in active:
        ref = raid_refs[item.id]
        overdue = item.due_date is not None and item.due_date < report.reporting_date
        if item.kind == "dependency" and item.critical and overdue and item.committed_resolution_date is None:
            days = (report.reporting_date - item.due_date).days
            record("dependencies", HealthStatus.RED,
                   f"{item.title} is {days} days overdue with no revised committed resolution date. Affects: {', '.join(item.affects)}.", [ref])
        if item.kind == "scope" and item.material and not item.impact_assessed:
            record("scope", HealthStatus.AMBER, f"Material scope change remains unassessed: {item.title}.", [ref])
        if item.kind == "action" and item.important and overdue:
            record("actions", HealthStatus.AMBER, f"Important action overdue since {item.due_date}: {item.title}.", [ref])
        # Active material risks/issues/dependencies and unassessed scope require escalation.
        requires_escalation = item.kind in {"risk", "dependency"} or (item.kind == "scope" and not item.impact_assessed)
        if item.material and requires_escalation and not item.escalated:
            record("governance", HealthStatus.AMBER, f"Material exposure has no formal escalation: {item.title}.", [ref])

    for index, milestone in enumerate(bundle.milestone_plan.milestones):
        if not milestone.critical_path or milestone.completed:
            continue
        slipped = milestone.forecast is not None and (milestone.forecast - milestone.baseline).days >= MATERIAL_SLIPPAGE_DAYS
        unknown_overdue = milestone.forecast is None and milestone.baseline < report.reporting_date
        if slipped or unknown_overdue:
            forecast = str(milestone.forecast) if milestone.forecast else "TBC"
            record("schedule", HealthStatus.AMBER,
                   f"Critical-path milestone {milestone.title}: baseline {milestone.baseline}, forecast {forecast}.",
                   [f"milestone_plan.json#/milestones/{index}"])

    quality_signals = [
        (quality.sev2_open >= SIGNIFICANT_SEV2_COUNT, f"{quality.sev2_open} Severity-2 defects remain open (threshold {SIGNIFICANT_SEV2_COUNT}).", "sev2_open"),
        (quality.sev2_reopened > 0, f"{quality.sev2_reopened} Severity-2 defects have reopened.", "sev2_reopened"),
        (quality.regression_testing != "COMPLETED", f"Regression testing is {quality.regression_testing}.", "regression_testing"),
        (quality.accessibility_testing != "COMPLETED", f"Accessibility testing is {quality.accessibility_testing}.", "accessibility_testing"),
        (quality.proctoring_e2e_validation != "COMPLETED", f"Proctoring E2E validation is {quality.proctoring_e2e_validation}.", "proctoring_e2e_validation"),
        (quality.sev1_open > 0, f"{quality.sev1_open} Severity-1 defects remain open.", "sev1_open"),
    ]
    for triggered, description, field in quality_signals:
        if triggered:
            record("quality", HealthStatus.AMBER, description, [f"defect_summary.json#/{field}"])

    blockers = [item for item in active if item.release_blocker]
    for item in blockers:
        dimension = {"dependency": "dependencies", "risk": "governance", "scope": "scope", "action": "actions"}[item.kind]
        record(dimension, HealthStatus.RED, f"Explicit release blocker: {item.title}.", [raid_refs[item.id]])

    sources = {
        "dependencies": "raid_log.json#/items", "scope": "raid_log.json#/items",
        "actions": "raid_log.json#/items", "governance": "raid_log.json#/items",
        "schedule": "milestone_plan.json#/milestones", "quality": "defect_summary.json",
    }
    for dimension in HealthDimensions.model_fields:
        if getattr(dimensions, dimension) == HealthStatus.GREEN:
            evidence.append(Evidence(dimension=dimension,
                description=f"No configured {dimension} risk rule triggered in the supplied snapshot.",
                references=[sources[dimension]]))

    overall = HealthStatus.RED if blockers else (
        HealthStatus.AMBER if any(value != HealthStatus.GREEN for value in dimensions.model_dump().values())
        else HealthStatus.GREEN
    )
    actions: list[LeadershipAction] = []
    # Group interventions to avoid repeated recommendations for related signals.
    if dimensions.dependencies != HealthStatus.GREEN or dimensions.governance != HealthStatus.GREEN:
        dependency_names = [item.title for item in active if item.kind == "dependency" and item.material]
        description = (f"Escalate the dependency: {', '.join(dependency_names)}; commit owners and resolution dates."
                       if dependency_names else "Escalate material exposures and agree accountable owners and resolution dates.")
        actions.append(LeadershipAction(description=description))
    if any(getattr(dimensions, name) != HealthStatus.GREEN for name in ("schedule", "scope", "actions")):
        actions.append(LeadershipAction(description="Reforecast the critical path and validate UAT feasibility; assess scope impact and close overdue actions."))
    if dimensions.quality != HealthStatus.GREEN:
        actions.append(LeadershipAction(description="Produce a scoring defect recovery and regression plan." if quality.scoring_sev2 else "Produce a quality recovery and regression plan."))

    return Assessment(
        project=report.project, reported_health=report.reported_health, assessed_health=overall,
        status_conflict=report.reported_health != overall,
        confidence=Confidence.HIGH,
        leadership_attention_required=overall != HealthStatus.GREEN,
        health_dimensions=dimensions, evidence=evidence, recommended_leadership_actions=actions,
    )


def calculate_normalized_assessment(
    report: WeeklyStatusReport, evidence: list[NormalizedEvidence]
) -> Assessment:
    """Evaluate canonical evidence using the existing operational rule policies.

    Narrative evidence is retained for challenges, but cannot fill missing
    operational facts or override structured facts merely by being HIGH confidence.
    """
    from app.models.input_evidence import DefectSummary, Milestone, MilestonePlan, RaidItem, RaidLog
    from app.models.normalized_evidence import SourceType

    if any(item.project_id != report.project for item in evidence):
        raise ValueError("Evidence project does not match assessment project")
    by_id: dict[str, NormalizedEvidence] = {}
    for item in evidence:
        if item.evidence_id in by_id and by_id[item.evidence_id] != item:
            raise ValueError("Conflicting evidence identifiers")
        by_id[item.evidence_id] = item
    records = list(by_id.values())
    raid = [item for item in records if item.source_type == SourceType.RAID_LOG and item.category != "raid_snapshot"]
    milestones = [item for item in records if item.source_type == SourceType.MILESTONE_PLAN]
    quality = [item for item in records if item.source_type == SourceType.QUALITY_DATA]
    if len(quality) != 1:
        raise ValueError("Exactly one structured quality snapshot is required")
    if any(item.evidence_kind != "operational_record" for item in raid + milestones + quality):
        raise ValueError("Operational rules require operational records")
    bundle = ProjectEvidence(
        weekly_status=report,
        raid=RaidLog(project=report.project, reporting_date=report.reporting_date,
                     items=[RaidItem.model_validate(item.metadata["record"]) for item in raid]),
        milestone_plan=MilestonePlan(project=report.project, reporting_date=report.reporting_date,
                                    milestones=[Milestone.model_validate(item.metadata["record"]) for item in milestones]),
        quality=DefectSummary.model_validate(quality[0].metadata["record"]),
    )
    result = _calculate_operational_assessment(bundle)
    reference_ids = {
        **{f"raid_log.json#/items/{i}": [item.evidence_id] for i, item in enumerate(raid)},
        **{f"milestone_plan.json#/milestones/{i}": [item.evidence_id] for i, item in enumerate(milestones)},
        "raid_log.json#/items": [item.evidence_id for item in records if item.source_type == SourceType.RAID_LOG],
        "milestone_plan.json#/milestones": [item.evidence_id for item in milestones],
        "defect_summary.json": [quality[0].evidence_id],
    }
    for finding in result.evidence:
        finding.references = sorted({identifier for ref in finding.references
                                     for identifier in reference_ids.get(ref, reference_ids["defect_summary.json"]
                                         if ref.startswith("defect_summary.json#/") else [])})
        if not finding.references:
            raise ValueError("Rule conclusion has no source evidence")
    return result


def calculate_assessment(bundle: ProjectEvidence) -> Assessment:
    """Compatibility facade for the original deterministic endpoint."""
    from app.services.evidence_adapters import adapt_structured

    normalized = adapt_structured(bundle)
    result = calculate_normalized_assessment(bundle.weekly_status, normalized)
    references = {item.evidence_id: item.source_reference for item in normalized}
    for finding in result.evidence:
        finding.references = sorted({references[identifier] for identifier in finding.references})
    return result
