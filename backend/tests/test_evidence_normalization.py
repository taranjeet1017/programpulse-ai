"""Evidence quality tests; no real OpenAI requests."""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.extraction import StatusReportExtraction
from app.services.evidence_normalizer import normalize_due_date, normalize_evidence
from test_ai_extraction import extracted_payload, provider_payload, mock_provider

REPORT_DATE = date(2026, 9, 18)
SNIPPET = "Proctoring certification was planned for 9 September."
REPORT = "Reporting date: 2026-09-18\n" + SNIPPET


def extraction(due_date: str | None = None) -> StatusReportExtraction:
    payload = extracted_payload()
    payload["reporting_date"] = "2026-09-18"
    item = payload["dependencies"][0]
    item.update(source_snippet=SNIPPET, description=SNIPPET, due_date=due_date,
                source_section="Delivery update", evidence_key="proctoring-certification-delay")
    return StatusReportExtraction.model_validate(payload)


@pytest.mark.parametrize("proposed", [None, "9099-09-09", "2025-09-09", "2026-09-09"])
def test_partial_date_uses_supported_reporting_context(proposed: str | None) -> None:
    result = normalize_evidence(extraction(proposed), REPORT)
    assert result.dependencies[0].due_date == date(2026, 9, 9)


@pytest.mark.parametrize("snippet,context", [
    (SNIPPET, None),
    ("Certification was planned for 9 September next year.", REPORT_DATE),
    ("Certification was planned for 9 September; year unknown.", REPORT_DATE),
    ("Certification was planned for 9 September or 10 September.", REPORT_DATE),
    ("Certification was planned for 9 September.", date(2026, 1, 5)),
    ("Certification was planned for 31 December.", date(2026, 1, 5)),
    ("Certification was planned for 5 January.", date(2026, 12, 28)),
    ("Certification was planned for 31 September.", REPORT_DATE),
    ("Certification was planned for next sprint.", REPORT_DATE),
    ("Certification was planned for 09/09.", REPORT_DATE),
])
def test_ambiguous_or_unsupported_date_is_null(snippet: str, context: date | None) -> None:
    assert normalize_due_date(snippet, date(2026, 9, 9), context) is None


def test_model_invented_reporting_context_cannot_resolve_date() -> None:
    assert normalize_evidence(extraction(), SNIPPET).dependencies[0].due_date is None


@pytest.mark.parametrize("source,expected", [
    ("Planned for 9 September 2025.", date(2025, 9, 9)),
    ("Due September 9, 2026.", date(2026, 9, 9)),
    ("Due 2027-01-05.", date(2027, 1, 5)),
    ("Due 9 September 9099.", None),
])
def test_explicit_dates_take_precedence(source: str, expected: date | None) -> None:
    assert normalize_due_date(source, None, REPORT_DATE) == expected


def test_implausible_due_year_cleared_at_model_boundary() -> None:
    assert extraction("9099-09-09").dependencies[0].due_date is None


@pytest.mark.parametrize("field", ["reporting_date", "reported_release_date"])
def test_implausible_metadata_year_rejected(field: str) -> None:
    payload = extracted_payload()
    payload[field] = "9099-09-09"
    with pytest.raises(ValidationError, match="between 1900 and 2100"):
        StatusReportExtraction.model_validate(payload)


def test_claim_confidence_and_traceability_unchanged() -> None:
    payload = extracted_payload()
    claim = dict(payload["dependencies"][0])
    claim.update(description="Management anticipates no release impact.",
                 source_snippet="No release impact is currently anticipated.",
                 source_section="PM summary", confidence="HIGH", evidence_kind="reported_claim")
    payload["delivery_claims"] = [claim]
    before = StatusReportExtraction.model_validate(payload)
    result = normalize_evidence(before, claim["source_snippet"])
    assert result.delivery_claims[0].model_dump() == before.delivery_claims[0].model_dump()
    assert result.delivery_claims[0].evidence_kind == "reported_claim"
    assert result.delivery_claims[0].confidence == "HIGH"


def test_identity_shared_without_merging_or_losing_categories() -> None:
    before = extraction("9099-09-09")
    before.risks = [before.dependencies[0].model_copy(update={"category": "risk"})]
    before.schedule_signals = [before.dependencies[0].model_copy(update={"category": "schedule"})]
    result = normalize_evidence(before, REPORT)
    for item in (result.dependencies[0], result.risks[0], result.schedule_signals[0]):
        assert item.evidence_key == "proctoring-certification-delay"
        assert item.due_date == date(2026, 9, 9)
        for field in ("source_section", "source_snippet", "evidence_kind", "description"):
            assert getattr(item, field) == getattr(before.dependencies[0], field)
    assert result.dependencies[0].category != result.risks[0].category
    assert normalize_evidence(result, REPORT) == result
    assert before.dependencies[0].due_date is None  # Pure transformation.


def test_optional_evidence_key_preserves_legacy_input() -> None:
    result = StatusReportExtraction.model_validate(extracted_payload())
    assert result.dependencies[0].evidence_key is None


def test_mocked_endpoint_repairs_live_failure(mock_provider) -> None:
    payload = provider_payload()
    output = extraction().model_dump(mode="json")
    output["dependencies"][0]["due_date"] = "9099-09-09"
    payload["output"][0]["content"][0]["text"] = json.dumps(output)
    mock_provider(payload)
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})
    assert response.status_code == 200
    observation = response.json()["dependencies"][0]
    assert observation["due_date"] == "2026-09-09"
    assert observation["source_snippet"] == SNIPPET
    assert observation["evidence_key"] == "proctoring-certification-delay"


@pytest.mark.parametrize("header", [
    "Reporting date: 2026-09-18\nReporting date: 2025-09-18",
    "Release date: 2026-09-18",
])
def test_conflicting_or_unlabelled_reporting_context_stays_unknown(header: str) -> None:
    assert normalize_evidence(extraction(), header + "\n" + SNIPPET).dependencies[0].due_date is None
