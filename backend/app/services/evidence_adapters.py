"""Source adapters preserve facts; they do not assign health ratings."""
import hashlib
import json
import re

from app.models.extraction import OBSERVATION_FIELDS, StatusReportExtraction
from app.models.input_evidence import ProjectEvidence
from app.models.normalized_evidence import Dimension as D, NormalizedEvidence, SourceType as S


def stable_id(prefix: str, *parts: str) -> str:
    return prefix + "-" + hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:20]


def event_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


AI_DIMENSIONS = {
    "delivery_claims": [D.SCHEDULE, D.QUALITY], "risks": [D.GOVERNANCE],
    "dependencies": [D.DEPENDENCIES], "quality_signals": [D.QUALITY],
    "schedule_signals": [D.SCHEDULE], "scope_changes": [D.SCOPE],
    "actions": [D.ACTIONS], "governance_statements": [D.GOVERNANCE],
    "statements_requiring_validation": [D.GOVERNANCE],
}


def adapt_ai(extraction: StatusReportExtraction, bundle: ProjectEvidence) -> list[NormalizedEvidence]:
    result = []
    project = bundle.weekly_status.project
    for field in OBSERVATION_FIELDS:
        for index, item in enumerate(getattr(extraction, field)):
            result.append(NormalizedEvidence(
                evidence_id=stable_id("EV", project, "AI_STATUS_REPORT", field, item.model_dump_json()),
                evidence_key=item.evidence_key, project_id=project, category=field,
                dimensions=AI_DIMENSIONS[field], description=item.description,
                evidence_kind=item.evidence_kind, severity=item.severity_hint, owner=item.owner,
                due_date=item.due_date, status=item.status, impact=item.impact,
                source_type=S.AI_STATUS_REPORT, source_name="weekly_status_report.md",
                source_section=item.source_section, source_snippet=item.source_snippet,
                source_reference=f"weekly_status_report.md#extraction/{field}/{index}",
                extraction_confidence=item.confidence,
                # A past date alone does not prove an item remains open.
                is_overdue=None, is_critical=None,
            ))
    return result


def adapt_structured(bundle: ProjectEvidence) -> list[NormalizedEvidence]:
    project = bundle.weekly_status.project
    as_of = bundle.weekly_status.reporting_date
    result = []
    result.append(NormalizedEvidence(
        evidence_id=stable_id("EV", project, "RAID_LOG", "snapshot"),
        evidence_key="raid-snapshot", project_id=project, category="raid_snapshot",
        dimensions=[D.DEPENDENCIES, D.SCOPE, D.ACTIONS, D.GOVERNANCE],
        description=f"RAID snapshot contains {len(bundle.raid.items)} entries.",
        evidence_kind="operational_record", source_type=S.RAID_LOG,
        source_name="raid_log.json", source_section="/items", source_reference="raid_log.json#/items",
        metadata={"record_count": len(bundle.raid.items)},
    ))
    dimensions = {"dependency": [D.DEPENDENCIES, D.GOVERNANCE], "risk": [D.GOVERNANCE],
                  "scope": [D.SCOPE, D.GOVERNANCE], "action": [D.ACTIONS]}
    for index, item in enumerate(bundle.raid.items):
        result.append(NormalizedEvidence(
            evidence_id=stable_id("EV", project, "RAID_LOG", item.id),
            evidence_key=item.evidence_key or event_key(item.title), project_id=project,
            category=item.kind, dimensions=dimensions[item.kind], description=item.title,
            evidence_kind="operational_record", due_date=item.due_date, status=item.status,
            impact=", ".join(item.affects) or None, source_type=S.RAID_LOG,
            source_name="raid_log.json", source_section=f"/items/{index}",
            source_reference=f"raid_log.json#/items/{index}",
            is_overdue=item.status == "OPEN" and item.due_date is not None and item.due_date < as_of,
            is_critical=item.critical, metadata={"record": item.model_dump(mode="json")},
        ))
    for index, item in enumerate(bundle.milestone_plan.milestones):
        result.append(NormalizedEvidence(
            evidence_id=stable_id("EV", project, "MILESTONE_PLAN", item.id),
            evidence_key=item.evidence_key or event_key(item.title), project_id=project,
            category="milestone", dimensions=[D.SCHEDULE], description=item.title,
            evidence_kind="operational_record", due_date=item.baseline,
            status="COMPLETED" if item.completed else "OPEN", source_type=S.MILESTONE_PLAN,
            source_name="milestone_plan.json", source_section=f"/milestones/{index}",
            source_reference=f"milestone_plan.json#/milestones/{index}",
            is_overdue=not item.completed and item.baseline < as_of, is_critical=item.critical_path,
            metadata={"record": item.model_dump(mode="json")},
        ))
    quality = bundle.quality
    result.append(NormalizedEvidence(
        evidence_id=stable_id("EV", project, "QUALITY_DATA", str(as_of)), project_id=project,
        evidence_key="quality-snapshot", category="quality_snapshot", dimensions=[D.QUALITY],
        description=f"{quality.sev2_open} open Sev-2 defects; {quality.sev2_reopened} reopened; "
                    f"regression {quality.regression_testing}; accessibility {quality.accessibility_testing}.",
        evidence_kind="operational_record", source_type=S.QUALITY_DATA,
        source_name="defect_summary.json", source_section="/", source_reference="defect_summary.json",
        metadata={"record": quality.model_dump(mode="json")},
    ))
    return result
