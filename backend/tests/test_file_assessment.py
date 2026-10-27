"""Upload validation runs before the mocked provider boundary."""
from unittest.mock import Mock
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import assessment_orchestrator
from app.services.sample_loader import SAMPLE_DIRECTORY
from app.services.openai_evidence_extractor import ExtractionError
from test_ai_assessment import extraction_result

PATH = "/api/v1/ai/assess-files"

@pytest.fixture
def files():
    return {field: (name, (SAMPLE_DIRECTORY / name).read_bytes()) for field, name in (
        ("status_report", "weekly_status_report.md"), ("raid_log", "raid_log.json"),
        ("milestone_plan", "milestone_plan.json"), ("quality_summary", "defect_summary.json"))}

@pytest.fixture
def extractor(monkeypatch, extraction_result):
    mock = Mock(return_value=extraction_result)
    monkeypatch.setattr(assessment_orchestrator, "extract_status_report", mock)
    return mock


def test_valid_upload_one_call_summary_and_cleanup(files, extractor, monkeypatch):
    import starlette.formparsers as parser
    original = parser.SpooledTemporaryFile
    handles = []
    def track(*args, **kwargs):
        file = original(*args, **kwargs)
        handles.append(file)
        return file
    monkeypatch.setattr(parser, "SpooledTemporaryFile", track)
    before = {p.name: p.read_bytes() for p in SAMPLE_DIRECTORY.iterdir() if p.is_file()}
    files["raid_log"] = ("my-raid.json", files["raid_log"][1])
    response = TestClient(app).post(PATH, files=files)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reported_health"] == "GREEN"
    assert data["programpulse_health"] == "AMBER"
    assert data["status_conflict"] is True
    assert len(data["dimension_summary"]) == 6
    assert next(d for d in data["dimension_summary"] if d["dimension"] == "DEPENDENCIES")["status"] == "RED"
    assert data["top_governance_challenges"] and data["top_recommended_actions"]
    assert "evidence_catalog" not in data
    assert any(e["source_name"] == "my-raid.json" for e in data["key_evidence"])
    assert response.headers["cache-control"] == "no-store"
    extractor.assert_called_once()
    assert len(handles) == 4 and all(h.closed for h in handles)
    assert before == {p.name: p.read_bytes() for p in SAMPLE_DIRECTORY.iterdir() if p.is_file()}

@pytest.mark.parametrize("field,name,data,reason", [
    ("status_report", "report.rtf", b"text", "extension"),
    ("status_report", "report.md", b"  ", "empty"),
    ("status_report", "report.txt", b"no headers", "metadata"),
    ("status_report", "report.md", b"x" * 100001, "size"),
    ("raid_log", "raid.json", b"{", "json"),
    ("milestone_plan", "plan.json", b"{}", "schema"),
    ("quality_summary", "quality.json", b"\xff", "encoding"),
    ("quality_summary", "quality.json", b"x" * 1000001, "size"),
])
def test_invalid_file_before_extraction(files, extractor, field, name, data, reason):
    files[field] = (name, data)
    response = TestClient(app).post(PATH, files=files)
    assert response.status_code == 422
    assert response.json()["detail"].items() >= {"code": "invalid_file", "field": field, "reason": reason}.items()
    extractor.assert_not_called()

@pytest.mark.parametrize("field", ["status_report", "raid_log", "milestone_plan", "quality_summary"])
def test_missing_file(files, extractor, field):
    del files[field]
    assert TestClient(app).post(PATH, files=files).status_code == 422
    extractor.assert_not_called()


def test_snapshot_mismatch(files, extractor):
    data = json.loads(files["raid_log"][1]); data["project"] = "Different project"
    files["raid_log"] = ("raid.json", json.dumps(data))
    response = TestClient(app).post(PATH, files=files)
    assert response.status_code == 422
    assert response.json()["detail"]["reason"] == "snapshot"
    extractor.assert_not_called()

@pytest.mark.parametrize("code,status", [("not_configured",503),("timeout",504),("upstream_failure",502),("invalid_output",502)])
def test_provider_errors_safe(files, extractor, code, status):
    extractor.side_effect = ExtractionError(code, "secret-provider-detail")
    response = TestClient(app).post(PATH, files=files)
    assert response.status_code == status
    assert "secret-provider-detail" not in response.text
    extractor.assert_called_once()


def test_total_size_limit(extractor):
    response = TestClient(app).post(PATH, content=b"x" * 3_200_001,
        headers={"Content-Type": "multipart/form-data; boundary=abc", "Origin": "http://localhost:3000"})
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    extractor.assert_not_called()


def test_uploaded_project_identity_is_not_fixed_to_assesspro(files, extractor):
    old = extractor.return_value.extraction.project_name
    new = "Customer Platform Renewal"
    for field, (name, content) in list(files.items()):
        files[field] = (name, content.decode().replace(old, new).encode())
    extractor.return_value.extraction.project_name = new
    response = TestClient(app).post(PATH, files=files)
    assert response.status_code == 200
    assert response.json()["project"] == new
    extractor.assert_called_once()
