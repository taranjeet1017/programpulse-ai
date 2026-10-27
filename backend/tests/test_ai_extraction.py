"""Exercise the real SDK parser against mocked HTTP, never a paid API."""
import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from pydantic import ValidationError

from app import config
from app.api import ai_extraction
from app.main import app
from app.models.extraction import OBSERVATION_FIELDS, StatusReportExtraction
from app.services import openai_evidence_extractor as extractor

REPORT = "Project: Example. Overall status GREEN. Certification remains pending."


def extracted_payload() -> dict:
    item = dict(category="certification", description="Certification remains pending.",
                evidence_kind="reported_observation", severity_hint=None, owner=None,
                due_date=None, status="pending", source_section=None,
                source_snippet="Certification remains pending.", impact=None, confidence="HIGH")
    return dict(project_name="Example", reporting_date=None, reported_health="GREEN",
                reported_release_date=None,
                **{name: [item] if name == "dependencies" else [] for name in OBSERVATION_FIELDS})


def provider_payload() -> dict:
    return {
        "id": "resp_mock", "object": "response", "created_at": 0,
        "model": "test-model-snapshot", "status": "completed", "error": None,
        "incomplete_details": None, "instructions": None, "metadata": {},
        "parallel_tool_calls": False, "tools": [], "tool_choice": "auto",
        "output": [{"type": "message", "id": "msg_mock", "role": "assistant",
                    "status": "completed", "content": [{"type": "output_text",
                    "text": json.dumps(extracted_payload()), "annotations": []}]}],
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
                  "input_tokens_details": {"cached_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 0}},
    }


@pytest.fixture
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> Callable:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")

    def install(payload: dict | None = None, status: int = 200,
                timeout: bool = False) -> list[dict]:
        requests: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            assert request.url.path == "/v1/responses"
            if timeout:
                raise httpx.ReadTimeout("private provider diagnostic", request=request)
            return httpx.Response(status, json=payload if payload is not None else provider_payload())

        def factory(**kwargs: object) -> OpenAI:
            return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

        monkeypatch.setattr(extractor, "OpenAI", factory)
        return requests

    return install


def test_structured_extraction_uses_real_sdk_parser(mock_provider: Callable) -> None:
    requests = mock_provider()
    result = extractor.extract_status_report(REPORT)
    assert isinstance(result.extraction, StatusReportExtraction)
    assert result.extraction.reported_health == "GREEN"
    assert result.extraction.dependencies[0].owner is None
    assert result.extraction.dependencies[0].due_date is None
    assert result.usage.model_dump() == dict(model="test-model-snapshot", input_tokens=100,
                                            output_tokens=50, total_tokens=150)
    request = requests[0]
    assert request["input"][1] == {"role": "user", "content": REPORT}
    assert "Do not determine final project health" in request["input"][0]["content"]
    assert request["store"] is False
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True
    schema = request["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert "assessed_health" not in schema["properties"]


@pytest.mark.parametrize("model,expected", [(None, "gpt-5.6-luna"), ("", "gpt-5.6-luna"), ("custom-model", "custom-model")])
def test_model_configuration(mock_provider: Callable, monkeypatch: pytest.MonkeyPatch,
                             model: str | None, expected: str) -> None:
    requests = mock_provider()
    if model is not None:
        monkeypatch.setenv("OPENAI_MODEL", model)
    extractor.extract_status_report(REPORT)
    assert requests[0]["model"] == expected


def test_dotenv_and_environment_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=file-secret\nOPENAI_MODEL=file-model\n")
    settings = config.get_openai_settings()
    assert settings.api_key.get_secret_value() == "file-secret"
    assert "file-secret" not in repr(settings)
    assert settings.model == "file-model"
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")
    monkeypatch.setenv("OPENAI_MODEL", "environment-model")
    assert config.get_openai_settings().model == "environment-model"
    assert config.get_openai_settings().api_key.get_secret_value() == "environment-secret"
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert config.get_openai_settings().api_key is None


@pytest.mark.parametrize("key", [None, "", "   ", "your_api_key_here"])
def test_missing_key(monkeypatch: pytest.MonkeyPatch, key: str | None) -> None:
    constructor = Mock(side_effect=AssertionError("No client should be created"))
    monkeypatch.setattr(extractor, "OpenAI", constructor)
    if key is not None:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    with pytest.raises(extractor.ExtractionError, match="OPENAI_API_KEY") as error:
        extractor.extract_status_report(REPORT)
    assert error.value.code == "not_configured"
    constructor.assert_not_called()
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "not_configured"
        assert client.get("/api/v1/demo-ai-extraction").status_code == 503


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_errors_are_safe(mock_provider: Callable, caplog: pytest.LogCaptureFixture, status: int) -> None:
    requests = mock_provider({"error": {"message": "sk-test-not-real private provider diagnostic",
                                      "type": "api_error"}}, status=status)
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "upstream_failure"
    assert "sk-test-not-real" not in response.text + caplog.text
    assert "private provider diagnostic" not in response.text + caplog.text
    assert len(requests) == 1  # No automatic paid retry.


def test_timeout(mock_provider: Callable) -> None:
    mock_provider(timeout=True)
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})
    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "timeout"


@pytest.mark.parametrize("mode", ["refusal", "incomplete", "invalid_json", "invalid_schema", "untraceable"])
def test_invalid_outputs_are_rejected(mock_provider: Callable, mode: str) -> None:
    payload = provider_payload()
    if mode == "refusal":
        payload["output"][0]["content"] = [{"type": "refusal", "refusal": "private refusal detail"}]
    elif mode == "incomplete":
        payload["status"] = "incomplete"
        payload["incomplete_details"] = {"reason": "max_output_tokens"}
        payload["output"] = []
    elif mode == "invalid_json":
        payload["output"][0]["content"][0]["text"] = "not json"
    else:
        output = extracted_payload()
        if mode == "invalid_schema":
            output["assessed_health"] = "RED"
        else:
            output["dependencies"][0]["source_snippet"] = "An invented quotation."
        payload["output"][0]["content"][0]["text"] = json.dumps(output)
    mock_provider(payload)
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "invalid_output"
    assert "private refusal detail" not in response.text


def test_missing_usage_is_null(mock_provider: Callable) -> None:
    payload = provider_payload()
    payload["usage"] = None
    mock_provider(payload)
    assert extractor.extract_status_report(REPORT).usage.total_tokens is None


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": " \n\t"}, {"text": None},
                                  {"text": 123}, {"text": "a" * 100_001}, {"text": REPORT, "model": "override"}])
def test_endpoint_validation(body: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    service = Mock(side_effect=AssertionError("Invalid input must not call provider"))
    monkeypatch.setattr(ai_extraction, "extract_status_report", service)
    with TestClient(app) as client:
        assert client.post("/api/v1/ai/extract-status-report", json=body).status_code == 422
    service.assert_not_called()


def test_direct_service_rejects_blank() -> None:
    with pytest.raises(ValidationError):
        extractor.extract_status_report("   ")


def test_post_returns_bare_typed_extraction(mock_provider: Callable) -> None:
    mock_provider()
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})
    assert response.status_code == 200
    assert response.json() == extracted_payload()
    assert response.headers["cache-control"] == "no-store"


def test_demo_reads_current_file(mock_provider: Callable, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    requests = mock_provider()
    monkeypatch.setattr(ai_extraction, "SAMPLE_DIRECTORY", tmp_path)
    report = tmp_path / "weekly_status_report.md"
    report.write_text(REPORT)
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-ai-extraction")
        assert response.status_code == 200
        assert response.json()["extraction"] == extracted_payload()
        assert response.json()["usage"]["total_tokens"] == 150
        assert response.headers["cache-control"] == "no-store"
        report.write_text(REPORT + " A new project update.")
        assert client.get("/api/v1/demo-ai-extraction").status_code == 200
    assert requests[0]["input"][1]["content"] == REPORT
    assert requests[1]["input"][1]["content"] == report.read_text()


@pytest.mark.parametrize("content", [None, "   "])
def test_unavailable_demo_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str | None) -> None:
    monkeypatch.setattr(ai_extraction, "SAMPLE_DIRECTORY", tmp_path)
    if content is not None:
        (tmp_path / "weekly_status_report.md").write_text(content)
    with TestClient(app) as client:
        assert client.get("/api/v1/demo-ai-extraction").status_code == 503


def test_deterministic_and_docs_remain_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extractor, "OpenAI", Mock(side_effect=AssertionError("AI must not be called")))
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "service": "ProgramPulse AI"}
        result = client.get("/api/v1/demo-assessment")
        assert result.status_code == 200
        assert result.json()["assessed_health"] == "AMBER"
        docs = client.get("/docs")
        assert docs.status_code == 200
        assert "/openapi.json" in docs.text
        schema = client.get("/openapi.json").json()
        assert "post" in schema["paths"]["/api/v1/ai/extract-status-report"]
        assert "get" in schema["paths"]["/api/v1/demo-ai-extraction"]
        assert "StatusReportExtraction" in schema["components"]["schemas"]
