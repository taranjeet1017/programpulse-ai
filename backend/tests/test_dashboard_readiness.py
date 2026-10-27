"""API readiness contracts and deterministic presentation; never live AI."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.normalized_evidence import Dimension, SourceType
from app.models.program_assessment import GovernanceChallenge
from app.services import assessment_orchestrator as orchestrator
from app.services.challenge_consolidation import consolidate_challenges
from app.services.dashboard_assessment import summarize_assessment, KEY_EVIDENCE_LIMIT
from app.services.evidence_adapters import adapt_ai, adapt_structured
from app.services.evidence_consolidation import consolidate
from app.services.governance_challenges import generate_challenges
from app.services.health_rules import calculate_normalized_assessment
from app.services.sample_loader import load_sample_evidence
from test_ai_assessment import extraction_result, mocked_extraction


def challenge(identifier: str, key: str | None = "same-conflict", severity: str = "AMBER") -> GovernanceChallenge:
    return GovernanceChallenge(
        challenge_id=identifier, reported_claim="Claim " + identifier,
        reported_source="report.md#" + identifier, claim_evidence_ids=["claim-" + identifier],
        assessment="REQUIRES_VALIDATION", reason="Reason " + identifier, severity=severity,
        supporting_evidence_ids=["support-" + identifier], leadership_relevance="Reconcile the source.",
        conflict_key=key,
    )


def test_consolidation_preserves_all_provenance_and_highest_severity() -> None:
    a, b = challenge("a"), challenge("b", severity="RED")
    merged, = consolidate_challenges([b, a])
    assert merged.severity == "RED"
    assert set(merged.supporting_evidence_ids) == {"support-a", "support-b"}
    assert set(merged.claim_evidence_ids) == {"claim-a", "claim-b"}
    assert {p.reported_source for p in merged.provenance} == {"report.md#a", "report.md#b"}
    assert {p.reason for p in merged.provenance} == {"Reason a", "Reason b"}
    assert {p.reported_claim for p in merged.provenance} == {"Claim a", "Claim b"}
    assert consolidate_challenges([a, b]) == [merged]
    assert consolidate_challenges([merged]) == [merged]


def test_distinct_challenges_are_not_merged() -> None:
    assert len(consolidate_challenges([challenge("a", "count-11-vs-6"), challenge("b", "count-12-vs-6")])) == 2
    assert len(consolidate_challenges([challenge("a", None), challenge("b", None)])) == 2


def test_duplicate_classification_findings_merge_across_categories(extraction_result) -> None:
    original = extraction_result.extraction.quality_signals[0]
    extraction_result.extraction.statements_requiring_validation.append(original.model_copy(update={
        "evidence_kind": "contradiction", "description": "Scoring defect counts differ between sources."}))
    extraction_result.extraction.risks.append(original.model_copy(update={
        "source_section": "Evidence clarification",
        "source_snippet": "The PM narrative calls all 11 Severity-2 defects scoring defects.",
    }))
    bundle = load_sample_evidence()
    combined = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    results = generate_challenges(calculate_normalized_assessment(bundle.weekly_status, combined.evidence), combined)
    counts = [c for c in results if "structured quality data records" in c.reason]
    assert len(counts) == 1
    assert len(results) == 4
    assert len(counts[0].claim_evidence_ids) == 3
    assert len(counts[0].provenance) == 4  # Three numeric checks plus narrative contradiction.
    ids = {item.evidence_id for item in combined.evidence}
    assert set(counts[0].supporting_evidence_ids + counts[0].claim_evidence_ids) <= ids


def test_different_reported_counts_remain_distinct(extraction_result) -> None:
    observation = extraction_result.extraction.quality_signals[0].model_copy(update={
        "source_snippet": "12 Severity-2 scoring defects remain open.", "description": "Twelve scoring defects."})
    extraction_result.extraction.quality_signals.append(observation)
    bundle = load_sample_evidence()
    combined = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    results = generate_challenges(calculate_normalized_assessment(bundle.weekly_status, combined.evidence), combined)
    assert len([c for c in results if "structured quality data records" in c.reason]) == 2


def test_reason_details_are_exact_rule_evidence(mocked_extraction: Mock) -> None:
    result = orchestrator.assess_ai_sample()
    ids = {item.evidence_id for item in result.evidence_catalog}
    for dimension in result.health_dimensions.values():
        assert dimension.reasons == [detail.reason for detail in dimension.reason_details]
        assert set(dimension.supporting_evidence_ids) == {
            identifier for detail in dimension.reason_details for identifier in detail.supporting_evidence_ids}
        assert all(detail.supporting_evidence_ids and set(detail.supporting_evidence_ids) <= ids
                   for detail in dimension.reason_details)
    schedule = result.health_dimensions[Dimension.SCHEDULE]
    by_id = {item.evidence_id: item for item in result.evidence_catalog}
    for detail in schedule.reason_details:
        assert len(detail.supporting_evidence_ids) == 1
        source = by_id[detail.supporting_evidence_ids[0]]
        assert source.description in detail.reason
        assert source.source_type == SourceType.MILESTONE_PLAN


def test_catalog_complete_shortlist_small_and_relevant(mocked_extraction: Mock) -> None:
    result = orchestrator.assess_ai_sample()
    assert result.key_evidence == result.evidence_catalog  # Deprecated legacy alias.
    assert 0 < len(result.key_evidence_ids) <= KEY_EVIDENCE_LIMIT
    assert len(result.key_evidence_ids) < len(result.evidence_catalog)
    by_id = {item.evidence_id: item for item in result.evidence_catalog}
    assert all(by_id[i].category != "raid_snapshot" for i in result.key_evidence_ids)
    red_ids = set(result.health_dimensions[Dimension.DEPENDENCIES].supporting_evidence_ids)
    assert red_ids & set(result.key_evidence_ids)
    references = {identifier for value in result.health_dimensions.values() for identifier in value.supporting_evidence_ids}
    references.update(identifier for c in result.governance_challenges for identifier in c.supporting_evidence_ids + c.claim_evidence_ids)
    references.update(identifier for a in result.recommended_actions for identifier in a.supporting_evidence_ids)
    assert references <= by_id.keys()


def test_summary_projection_no_additional_extraction(mocked_extraction: Mock) -> None:
    completed = orchestrator.assess_ai_sample()
    summary = summarize_assessment(completed)
    assert summarize_assessment(completed) == summary
    mocked_extraction.assert_called_once()
    assert summary.assessment_date.isoformat() == "2026-09-18"
    assert summary.programpulse_health == "AMBER"
    assert summary.reported_health == "GREEN"
    assert summary.status_conflict and summary.leadership_attention_required
    assert {item.dimension for item in summary.dimension_summary} == set(Dimension)
    assert summary.top_governance_challenges and summary.top_recommended_actions
    assert "evidence_catalog" not in summary.model_dump()
    assert "evidence_groups" not in summary.model_dump()
    assert all("metadata" not in item.model_dump() for item in summary.key_evidence)
    assert len(summary.model_dump_json()) < len(completed.model_dump_json())


def test_summary_endpoint_invokes_pipeline_once(mocked_extraction: Mock) -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-assessment/summary")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        data = response.json()
        assert "evidence_catalog" not in data
        assert len(data["dimension_summary"]) == 6
        assert data["programpulse_health"] == "AMBER"
        assert data["status_conflict"] is True
        assert data["top_governance_challenges"] and data["top_recommended_actions"]
        schema = client.get("/openapi.json").json()
        assert "get" in schema["paths"]["/api/v1/demo-ai-assessment/summary"]
    mocked_extraction.assert_called_once()


def test_detailed_endpoint_keeps_audit_evidence(mocked_extraction: Mock) -> None:
    with TestClient(app) as client:
        data = client.get("/api/v1/demo-ai-assessment").json()
    assert data["evidence_catalog"] == data["key_evidence"]
    assert len(data["evidence_catalog"]) > len(data["key_evidence_ids"])
    assert any(item["category"] == "raid_snapshot" for item in data["evidence_catalog"])
    assert data["health_dimensions"]["DEPENDENCIES"]["status"] == "RED"
    assert data["programpulse_assessment"]["overall_status"] == "AMBER"


def test_reporting_development_not_critical_schedule_still_amber() -> None:
    bundle = load_sample_evidence()
    reporting = next(item for item in bundle.milestone_plan.milestones if item.title == "Reporting development")
    assert reporting.critical_path is False
    result = calculate_normalized_assessment(bundle.weekly_status, adapt_structured(bundle))
    assert result.health_dimensions.schedule == "AMBER"
    assert result.health_dimensions.dependencies == "RED"
    assert result.assessed_health == "AMBER"
    assert result.status_conflict is True
    assert all("Reporting development" not in item.description for item in result.evidence if item.dimension == "schedule")


def test_summary_missing_key_is_safe() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-assessment/summary")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "not_configured"



def test_overall_green_and_on_track_position_consolidate(extraction_result) -> None:
    original = extraction_result.extraction.delivery_claims[0]
    extraction_result.extraction.delivery_claims.append(original.model_copy(update={
        "source_snippet": "Overall status is GREEN.", "description": "Management reports GREEN."}))
    bundle = load_sample_evidence()
    combined = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    challenges = generate_challenges(calculate_normalized_assessment(bundle.weekly_status, combined.evidence), combined)
    assert len(challenges) == 4
    delivery = next(c for c in challenges if "delivery confidence" in c.reason)
    assert len(delivery.provenance) == 2


def test_broad_contradiction_not_silently_folded_into_numeric_discrepancy(extraction_result) -> None:
    original = extraction_result.extraction.quality_signals[0]
    extraction_result.extraction.statements_requiring_validation.append(original.model_copy(update={
        "evidence_kind": "contradiction", "description": "Counts and release claims contradict evidence."}))
    bundle = load_sample_evidence()
    combined = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    challenges = generate_challenges(calculate_normalized_assessment(bundle.weekly_status, combined.evidence), combined)
    assert any(c.reason.startswith("The narrative contains conflicting") for c in challenges)
    assert len([c for c in challenges if "structured quality data records" in c.reason]) == 1
