"""Provider diagnostics use only mocked HTTP responses."""
import json
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from app.main import app
from app.services import openai_evidence_extractor as extractor
from app.services.extraction_diagnostics import log_failure
from test_ai_extraction import REPORT, extracted_payload, provider_payload


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> Callable:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-diagnostics")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")

    def install(payload: dict | None = None, status: int = 200, failure: str | None = None) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if failure == "connection":
                raise httpx.ConnectError("private transport detail", request=request)
            if failure == "timeout":
                raise httpx.ReadTimeout("private transport detail", request=request)
            return httpx.Response(status, json=payload if payload is not None else provider_payload(),
                                  headers={"x-request-id": "req_diagnostic_123"})

        def factory(**kwargs: object) -> OpenAI:
            return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        monkeypatch.setattr(extractor, "OpenAI", factory)
    return install


def diagnostic(caplog: pytest.LogCaptureFixture) -> dict:
    records = [r for r in caplog.records if r.name == "app.services.extraction_diagnostics"]
    assert len(records) == 1
    assert records[0].exc_info is None
    assert "\n" not in records[0].getMessage()
    return json.loads(records[0].getMessage())


def call() -> httpx.Response:
    with TestClient(app) as client:
        return client.post("/api/v1/ai/extract-status-report", json={"text": REPORT})


@pytest.mark.parametrize("status,code,category,exception", [
    (401, "invalid_api_key", "authentication", "AuthenticationError"),
    (403, "model_not_allowed", "permission_denied", "PermissionDeniedError"),
    (400, "invalid_json_schema", "bad_request", "BadRequestError"),
    (429, "rate_limit_exceeded", "rate_limit", "RateLimitError"),
    (429, "insufficient_quota", "insufficient_quota", "RateLimitError"),
    (500, "server_error", "provider_error", "InternalServerError"),
])
def test_provider_details(provider: Callable, caplog: pytest.LogCaptureFixture,
                          status: int, code: str, category: str, exception: str) -> None:
    message = "The request cannot be processed with this configuration."
    provider({"error": {"message": message, "code": code, "type": "invalid_request_error"}}, status)
    response = call()
    assert response.status_code == 502
    entry = diagnostic(caplog)
    assert entry["category"] == category
    assert entry["exception_class"] == exception
    assert entry["http_status"] == status
    assert entry["error_code"] == code
    assert entry["error_type"] == "invalid_request_error"
    assert entry["message"] == message
    assert entry["request_id"] == "req_diagnostic_123"
    assert entry["model"] == "configured-model"
    assert message not in response.text


@pytest.mark.parametrize("failure,status,exception", [
    ("connection", 502, "APIConnectionError"), ("timeout", 504, "APITimeoutError"),
])
def test_transport_details(provider: Callable, caplog: pytest.LogCaptureFixture,
                           failure: str, status: int, exception: str) -> None:
    provider(failure=failure)
    assert call().status_code == status
    entry = diagnostic(caplog)
    assert entry["category"] == failure
    assert entry["exception_class"] == exception
    assert entry["http_status"] is None
    assert entry["request_id"] is None
    assert "private transport detail" not in caplog.text


@pytest.mark.parametrize("mode,category", [
    ("refusal", "model_refusal"), ("incomplete", "incomplete_response"),
    ("truncated", "incomplete_response"), ("no_output", "missing_parsed_output"), ("validation", "structured_output_validation"),
    ("invalid_json", "structured_output_validation"), ("excerpt", "untraceable_excerpt"),
])
def test_output_details(provider: Callable, caplog: pytest.LogCaptureFixture, mode: str, category: str) -> None:
    payload = provider_payload()
    if mode == "refusal":
        payload["output"][0]["content"] = [{"type": "refusal", "refusal": "PRIVATE REFUSAL"}]
    elif mode == "truncated":
        payload.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        payload["output"][0]["content"][0]["text"] = '{"project_name": "unfinished'
    elif mode == "incomplete":
        payload.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"}, output=[])
    elif mode == "no_output":
        payload["output"] = []
    else:
        output = extracted_payload()
        if mode == "validation":
            output["reported_health"] = "PRIVATE INVALID VALUE"
        elif mode == "excerpt":
            output["dependencies"][0]["source_snippet"] = "PRIVATE EXCERPT"
        payload["output"][0]["content"][0]["text"] = (
            "PRIVATE INVALID JSON" if mode == "invalid_json" else json.dumps(output))
    provider(payload)
    response = call()
    assert response.status_code == 502
    entry = diagnostic(caplog)
    assert entry["category"] == category
    assert entry["model"] == "configured-model"
    assert entry["http_status"] == 200
    assert entry["request_id"] == "req_diagnostic_123"
    if mode in {"validation", "invalid_json"}:
        assert entry["exception_class"] == "ValidationError"
        assert entry["validation_error_types"]
    else:
        assert entry["request_id"] == "req_diagnostic_123"
    if mode in {"incomplete", "truncated"}:
        assert entry["reason"] == "max_output_tokens"
    assert "PRIVATE" not in caplog.text + response.text


@pytest.mark.parametrize("message", [
    "Incorrect API key provided: sk-test-diagnostics.", "Authorization: Bearer other-credential",
    "password=another-value", "Service returned unrelated-environment-credential",
    "Connect at https://user:pass@example.com",
])
def test_secret_suppression(provider: Callable, caplog: pytest.LogCaptureFixture,
                            monkeypatch: pytest.MonkeyPatch, message: str) -> None:
    monkeypatch.setenv("OTHER_SERVICE_TOKEN", "unrelated-environment-credential")
    provider({"error": {"message": message, "type": "invalid_request_error"}}, 400)
    response = call()
    assert response.status_code == 502
    assert diagnostic(caplog)["message"] == "[redacted sensitive diagnostic]"
    assert message not in caplog.text + response.text


def test_metadata_redaction_and_log_injection(caplog: pytest.LogCaptureFixture) -> None:
    log_failure(category="bad_request", model="secret-value", api_key="secret-value",
                message="Invalid schema.\nFORGED LOG ENTRY", request_id="secret-value",
                error_code="secret-value", error_type="secret-value", reason="secret-value")
    assert diagnostic(caplog)["message"] == "Invalid schema.\nFORGED LOG ENTRY"
    assert "secret-value" not in caplog.text


def test_missing_configuration(caplog: pytest.LogCaptureFixture) -> None:
    assert call().status_code == 503
    assert diagnostic(caplog)["category"] == "configuration"
