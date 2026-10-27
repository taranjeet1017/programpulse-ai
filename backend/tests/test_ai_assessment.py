"""End-to-end assurance with a mocked extraction boundary and no network."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.extraction import OBSERVATION_FIELDS, ExtractionResult, ExtractionUsage, StatusReportExtraction
from app.models.normalized_evidence import Dimension, NormalizedEvidence, SourceType
from app.services import assessment_orchestrator as orchestrator
from app.services.evidence_adapters import adapt_ai, adapt_structured
from app.services.evidence_consolidation import consolidate
from app.services.health_rules import calculate_normalized_assessment
from app.services.sample_loader import load_sample_evidence
from app.services.openai_evidence_extractor import ExtractionError
from test_assessment import clean_bundle


@pytest.fixture
def extraction_result() -> ExtractionResult:
    report = load_sample_evidence().weekly_status
    values = {name: [] for name in OBSERVATION_FIELDS}

    def item(quote: str, kind: str = "reported_claim", key: str | None = None) -> dict:
        assert quote in report.narrative
        return dict(category="delivery", description=quote, evidence_kind=kind,
                    severity_hint="HIGH", owner=None, due_date=None, status=None,
                    source_section="Delivery update", source_snippet=quote, impact=None,
                    confidence="HIGH", evidence_key=key)

    values["delivery_claims"] = [item("Development is broadly on track."),
                                  item("No release impact is currently anticipated.")]
    values["governance_statements"] = [item("No immediate escalation is required.")]
    event = item("Proctoring certification was planned for 9 September but is still pending.",
                 "reported_observation", "proctoring-certification-delay")
    for field in ("dependencies", "risks", "schedule_signals", "statements_requiring_validation"):
        values[field] = [event.copy()]
    values["quality_signals"] = [item("11 Severity-2 scoring defects remain open.", "reported_observation")]
    return ExtractionResult(
        extraction=StatusReportExtraction(project_name=report.project, reporting_date=report.reporting_date,
            reported_health=report.reported_health, reported_release_date=report.target_production_release, **values),
        usage=ExtractionUsage(model="mock-model", input_tokens=100, output_tokens=200, total_tokens=300),
    )


@pytest.fixture
def mocked_extraction(monkeypatch: pytest.MonkeyPatch, extraction_result: ExtractionResult) -> Mock:
    mock = Mock(return_value=extraction_result)
    monkeypatch.setattr(orchestrator, "extract_status_report", mock)
    return mock


def test_adapters_preserve_traceability(extraction_result: ExtractionResult) -> None:
    bundle = load_sample_evidence()
    ai = adapt_ai(extraction_result.extraction, bundle)
    records = adapt_structured(bundle)
    assert all(isinstance(item, NormalizedEvidence) for item in ai + records)
    assert {item.source_type for item in records} == {SourceType.RAID_LOG, SourceType.MILESTONE_PLAN, SourceType.QUALITY_DATA}
    assert all(item.source_name and item.source_reference for item in ai + records)
    assert all(item.source_snippet and item.source_section for item in ai)
    assert ai[0].evidence_kind == "reported_claim"
    assert ai[0].extraction_confidence == "HIGH"
    dependency = next(item for item in records if item.category == "dependency")
    assert dependency.is_overdue is True and dependency.is_critical is True
    assert dependency.due_date.isoformat() == "2026-09-09"


def test_consolidation_associates_all_three_sources(extraction_result: ExtractionResult) -> None:
    bundle = load_sample_evidence()
    result = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    group = next(group for group in result.groups if group.evidence_key == "proctoring-certification")
    records = [item for item in result.evidence if item.evidence_id in group.evidence_ids]
    assert {item.source_type for item in records} == {SourceType.RAID_LOG, SourceType.MILESTONE_PLAN, SourceType.AI_STATUS_REPORT}
    assert {Dimension.SCHEDULE, Dimension.DEPENDENCIES, Dimension.GOVERNANCE} <= set(group.dimensions)
    assert len({item.source_reference for item in records}) == len(records)


def test_repeated_mentions_do_not_increase_health_severity(extraction_result: ExtractionResult) -> None:
    bundle = load_sample_evidence()
    normalized = adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle)
    once = calculate_normalized_assessment(bundle.weekly_status, consolidate(normalized).evidence)
    repeated = calculate_normalized_assessment(bundle.weekly_status, consolidate(normalized * 5).evidence)
    assert once == repeated
    assert repeated.assessed_health == "AMBER"


def test_different_occurrences_keep_all_source_locations(extraction_result: ExtractionResult) -> None:
    bundle = load_sample_evidence()
    duplicate = extraction_result.extraction.dependencies[0].model_copy()
    extraction_result.extraction.dependencies.append(duplicate)
    evidence = consolidate(adapt_ai(extraction_result.extraction, bundle))
    dependencies = [item for item in evidence.evidence if item.category == "dependencies"]
    assert len(dependencies) == 2
    assert len({item.source_reference for item in dependencies}) == 2
    assert len({item.evidence_id for item in dependencies}) == 2


def test_end_to_end_result_and_one_call(mocked_extraction: Mock) -> None:
    result = orchestrator.assess_ai_sample()
    mocked_extraction.assert_called_once_with(load_sample_evidence().weekly_status.narrative)
    assert result.reported_health == "GREEN"
    assert result.programpulse_assessment.overall_status == "AMBER"
    assert result.programpulse_assessment.status_conflict is True
    assert result.programpulse_assessment.leadership_attention_required is True
    assert result.health_dimensions[Dimension.DEPENDENCIES].status == "RED"
    assert all(value.status == "AMBER" for key, value in result.health_dimensions.items() if key != Dimension.DEPENDENCIES)
    ids = {item.evidence_id for item in result.key_evidence}
    for value in result.health_dimensions.values():
        assert value.supporting_evidence_ids and set(value.supporting_evidence_ids) <= ids
    for value in result.governance_challenges:
        assert value.supporting_evidence_ids and set(value.supporting_evidence_ids) <= ids
        assert value.claim_evidence_ids and set(value.claim_evidence_ids) <= ids
    for value in result.recommended_actions:
        assert value.supporting_evidence_ids and set(value.supporting_evidence_ids) <= ids
    assert result.usage.total_tokens == 300
    assert "reported GREEN, evidenced AMBER" in result.executive_summary


def test_engine_receives_canonical_evidence(mocked_extraction: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Mock(wraps=calculate_normalized_assessment)
    monkeypatch.setattr(orchestrator, "calculate_normalized_assessment", engine)
    orchestrator.assess_ai_sample()
    passed = engine.call_args.args[1]
    assert all(isinstance(item, NormalizedEvidence) for item in passed)
    assert {item.source_type for item in passed} == set(SourceType)


def test_claims_challenged_and_contradictions_preserved(mocked_extraction: Mock) -> None:
    result = orchestrator.assess_ai_sample()
    challenged = [item for item in result.governance_challenges if item.assessment == "CHALLENGED"]
    assert len(challenged) == 3
    assert any("scoring Sev-2" in item.reason for item in result.governance_challenges)
    assert any(item.evidence_kind == "reported_claim" and "No release impact" in item.description for item in result.key_evidence)
    assert any(item.source_type == SourceType.QUALITY_DATA and item.metadata["record"]["scoring_sev2"] == 6 for item in result.key_evidence)


def test_ai_claims_never_override_structured_health(extraction_result: ExtractionResult) -> None:
    bundle = load_sample_evidence()
    result = calculate_normalized_assessment(bundle.weekly_status,
        adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    assert result.assessed_health == "AMBER"
    clean = clean_bundle()
    for field in OBSERVATION_FIELDS:
        for item in getattr(extraction_result.extraction, field):
            item.severity_hint = "CRITICAL"
    recovered = calculate_normalized_assessment(clean.weekly_status,
        adapt_structured(clean) + adapt_ai(extraction_result.extraction, clean))
    assert recovered.assessed_health == "GREEN"  # Model hints cannot set health.


def test_resolved_evidence_removes_challenges_and_actions(extraction_result: ExtractionResult, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.assessment_output import build_assessment
    bundle = clean_bundle()
    extraction_result.extraction.quality_signals = []
    combined = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    output = build_assessment(calculate_normalized_assessment(bundle.weekly_status, combined.evidence), combined, extraction_result.usage)
    assert output.programpulse_assessment.overall_status == "GREEN"
    assert output.governance_challenges == []
    assert output.recommended_actions == []


def test_ai_endpoint_and_openapi(mocked_extraction: Mock) -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-assessment")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["programpulse_assessment"]["overall_status"] == "AMBER"
        schema = client.get("/openapi.json").json()
        for path in ("/health", "/api/v1/demo-assessment", "/api/v1/demo-ai-extraction", "/api/v1/demo-ai-assessment"):
            assert "get" in schema["paths"][path]
        assert "post" in schema["paths"]["/api/v1/ai/extract-status-report"]
        assert client.get("/docs").status_code == 200
    mocked_extraction.assert_called_once()


def test_missing_key_safe_and_legacy_endpoint_works() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-assessment")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "not_configured"
        assert client.get("/api/v1/demo-assessment").json()["assessed_health"] == "AMBER"
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize("code,status", [("upstream_failure", 502), ("invalid_output", 502), ("timeout", 504)])
def test_safe_upstream_failure(mocked_extraction: Mock, code: str, status: int) -> None:
    mocked_extraction.side_effect = ExtractionError(code, "Safe failure.")
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-assessment")
    assert response.status_code == status
    assert response.json()["detail"]["message"] == "Safe failure."


def test_invalid_local_source_prevents_paid_request(mocked_extraction: Mock, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        orchestrator.assess_ai_sample(tmp_path)
    mocked_extraction.assert_not_called()


def test_mismatched_ai_project_rejected(mocked_extraction: Mock, extraction_result: ExtractionResult) -> None:
    extraction_result.extraction.project_name = "Different project"
    with pytest.raises(ExtractionError, match="project identity"):
        orchestrator.assess_ai_sample()


def test_explicit_blocker_remains_red(extraction_result: ExtractionResult) -> None:
    bundle = load_sample_evidence()
    bundle.raid.items[0].release_blocker = True
    combined = consolidate(adapt_structured(bundle) + adapt_ai(extraction_result.extraction, bundle))
    assert calculate_normalized_assessment(bundle.weekly_status, combined.evidence).assessed_health == "RED"


@pytest.mark.parametrize("field,value", [("reported_health", "RED"), ("reporting_date", "2026-09-19")])
def test_ai_metadata_disagreement_fails_safely(mocked_extraction: Mock, extraction_result: ExtractionResult,
                                             field: str, value: str) -> None:
    payload = extraction_result.extraction.model_dump(mode="json")
    payload[field] = value
    extraction_result.extraction = StatusReportExtraction.model_validate(payload)
    with TestClient(app) as client:
        assert client.get("/api/v1/demo-ai-assessment").status_code == 502


def test_conflicting_identifiers_are_rejected() -> None:
    bundle = load_sample_evidence()
    records = adapt_structured(bundle)
    conflict = records[1].model_copy(update={"description": "Conflicting fact"})
    with pytest.raises(ValueError, match="Conflicting evidence"):
        consolidate(records + [conflict])
    with pytest.raises(ValueError, match="Conflicting evidence"):
        calculate_normalized_assessment(bundle.weekly_status, records + [conflict])


def test_empty_raid_still_has_coverage_evidence() -> None:
    bundle = clean_bundle()
    bundle.raid.items = []
    result = calculate_normalized_assessment(bundle.weekly_status, adapt_structured(bundle))
    assert result.assessed_health == "GREEN"
    assert all(finding.references for finding in result.evidence)


def test_full_sdk_pipeline_uses_one_mocked_http_call(extraction_result: ExtractionResult, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import httpx
    from openai import OpenAI
    from app.services import openai_evidence_extractor
    from test_ai_extraction import provider_payload

    payload = provider_payload()
    payload["output"][0]["content"][0]["text"] = extraction_result.extraction.model_dump_json()
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=payload)

    def factory(**kwargs: object) -> OpenAI:
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-only")
    monkeypatch.setattr(openai_evidence_extractor, "OpenAI", factory)
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-assessment")
    assert response.status_code == 200
    assert response.json()["programpulse_assessment"]["overall_status"] == "AMBER"
    assert len(requests) == 1
    assert requests[0]["input"][1]["content"] == load_sample_evidence().weekly_status.narrative
