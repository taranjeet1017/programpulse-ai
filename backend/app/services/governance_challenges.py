"""Deterministic claim checks and recommendations, never model-generated health."""
import re

from app.models.assessment import Assessment, Evidence, HealthStatus
from app.models.normalized_evidence import ConsolidatedEvidence, SourceType
from app.models.program_assessment import GovernanceChallenge, RecommendedAction
from app.services.evidence_adapters import stable_id
from app.services.challenge_consolidation import consolidate_challenges


def adverse_findings(assessment: Assessment, dimensions: tuple[str, ...]) -> list[Evidence]:
    return [finding for finding in assessment.evidence if finding.dimension in dimensions
            and getattr(assessment.health_dimensions, finding.dimension) != HealthStatus.GREEN]


CLAIM_POLICIES = (
    (r"\b(on track|on schedule|progressing as planned)\b|\boverall (?:status|health)\s+(?:is |reported as |reported )?GREEN\b", ("schedule", "quality"),
     "Reported delivery confidence requires validation against schedule and quality pressure."),
    (r"\bno\b[^.!?]*\b(release|delivery)\s+impact\b|\b(release|delivery)\b[^.!?]*\bunaffected\b",
     ("dependencies", "schedule"), "The no-impact claim requires validation against dependency and critical-path exposure."),
    (r"\bno\b[^.!?]*\bescalation\b|\bescalation\b[^.!?]*\bnot\s+(required|needed)\b",
     ("dependencies", "governance"), "The escalation position conflicts with unresolved dependency or governance exposure."),
)


def generate_challenges(assessment: Assessment, consolidated: ConsolidatedEvidence) -> list[GovernanceChallenge]:
    challenges = []
    seen = set()
    related = {identifier: group.evidence_ids for group in consolidated.groups for identifier in group.evidence_ids}
    by_id = {item.evidence_id: item for item in consolidated.evidence}
    for item in consolidated.evidence:
        if item.source_type != SourceType.AI_STATUS_REPORT:
            continue
        quote = item.source_snippet or item.description
        count = re.search(
            r"\b(\d+)\s+(?:Severity[- ]?2|Sev[- ]?2)\s+(?:scoring\s+defects|defects\s+(?:as\s+)?scoring\s+defects)",
            quote, re.I)
        quality_conflicts = []
        if count:
            for operational in by_id.values():
                if operational.source_type == SourceType.QUALITY_DATA:
                    actual = operational.metadata["record"].get("scoring_sev2")
                    if actual is not None and int(count[1]) != actual:
                        quality_conflicts.append((operational, actual, stable_id(
                            "CONFLICT", item.project_id, "scoring_sev2", str(int(count[1])),
                            str(actual), operational.evidence_id)))
        if item.evidence_kind == "reported_claim":
            for pattern, dimensions, explanation in CLAIM_POLICIES:
                if not re.search(pattern, quote, re.I):
                    continue
                if re.search(r"\b(not|never)\s+(?:broadly\s+)?on (track|schedule)\b", quote, re.I):
                    continue
                findings = adverse_findings(assessment, dimensions)
                if not findings:
                    continue
                key = (" ".join(quote.lower().split()), dimensions)
                if key in seen:
                    continue
                seen.add(key)
                ids = sorted({identifier for finding in findings for identifier in finding.references})
                claim_ids = [other.evidence_id for other in consolidated.evidence
                             if other.source_type == SourceType.AI_STATUS_REPORT
                             and other.evidence_kind == "reported_claim"
                             and " ".join((other.source_snippet or other.description).lower().split()) == key[0]]
                conflict_key = None
                if dimensions == ("schedule", "quality") and re.search(
                    r"(?:^|[.!?]\s+)(?:development|project|delivery|overall status|overall health)\s+"
                    r"(?:(?:is|remains|reported as|reported)\s+)?(?:broadly\s+)?(?:on track|on schedule|GREEN)\b",
                    quote, re.I):
                    conflict_key = stable_id("CONFLICT", item.project_id, "overall_delivery_position", *ids)
                challenges.append(GovernanceChallenge(
                    conflict_key=conflict_key,
                    challenge_id=stable_id("CH", item.project_id, quote, ",".join(dimensions)),
                    reported_claim=quote, reported_source=item.source_reference,
                    claim_evidence_ids=claim_ids, assessment="CHALLENGED",
                    reason=explanation + " " + " ".join(finding.description for finding in findings[:3]),
                    severity="RED" if any(getattr(assessment.health_dimensions, d) == HealthStatus.RED for d in dimensions) else "AMBER",
                    supporting_evidence_ids=ids, leadership_relevance="Validate the claim and agree an accountable recovery or escalation decision.",
                ))
        elif item.evidence_kind == "contradiction":
            ids = related.get(item.evidence_id, [item.evidence_id])
            challenges.append(GovernanceChallenge(
                challenge_id=stable_id("CH", item.evidence_id), reported_claim=quote,
                reported_source=item.source_reference, claim_evidence_ids=[item.evidence_id],
                assessment="REQUIRES_VALIDATION", reason="The narrative contains conflicting statements requiring source review.",
                severity="AMBER", supporting_evidence_ids=ids,
                conflict_key=quality_conflicts[0][2] if len(quality_conflicts) == 1 and not re.search(
                    r"\b(release|escalation|milestone|scope|dependency|certification)\b|(?:Severity|Sev)[- ]?1",
                    quote + " " + item.description, re.I) else None,
                leadership_relevance="Reconcile conflicting source statements before relying on them.",
            ))
        # Preserve a concrete numeric discrepancy without relying on the LLM to
        # label it as a contradiction. This compares the source quotation only.
        for operational, actual, conflict_key in quality_conflicts:
            challenges.append(GovernanceChallenge(
                challenge_id=stable_id("CH", item.project_id, "scoring-count", item.evidence_id),
                reported_claim=quote, reported_source=item.source_reference,
                claim_evidence_ids=[item.evidence_id], assessment="REQUIRES_VALIDATION",
                reason=f"Narrative reports {count[1]} scoring Sev-2 defects; structured quality data records {actual}. Structured counts drive health rules.",
                severity="AMBER", supporting_evidence_ids=[operational.evidence_id],
                conflict_key=conflict_key,
                leadership_relevance="Reconcile defect classification and publish consistent counts.",
            ))
    return consolidate_challenges(challenges)


ACTION_POLICIES = (
    (("dependencies",), "Escalate dependency exposure and obtain owned recovery commitments."),
    (("schedule",), "Reforecast the critical path and validate UAT entry feasibility."),
    (("quality",), "Require a defect recovery plan and complete regression and testing readiness checks."),
    (("scope",), "Complete the material scope impact assessment and approve the resulting plan."),
    (("actions",), "Assign accountable owners and recovery dates to overdue actions."),
    (("governance",), "Formally escalate material exposures and record leadership decisions."),
)


def generate_actions(assessment: Assessment) -> list[RecommendedAction]:
    result = []
    for dimensions, description in ACTION_POLICIES:
        findings = adverse_findings(assessment, dimensions)
        if findings:
            result.append(RecommendedAction(
                action_id=stable_id("ACT", assessment.project, *dimensions), description=description,
                supporting_evidence_ids=sorted({identifier for finding in findings for identifier in finding.references}),
            ))
    return result
