"""OpenAI-specific extraction boundary; never invokes the governance engine."""
from pathlib import Path

from openai import (
    APIConnectionError, APIError, APIResponseValidationError, APITimeoutError,
    AuthenticationError, BadRequestError, OpenAI, PermissionDeniedError, RateLimitError,
)
from pydantic import ValidationError

from app.config import get_openai_settings
from app.services.extraction_diagnostics import log_failure
from app.services.evidence_normalizer import normalize_evidence
from app.models.extraction import (
    OBSERVATION_FIELDS, ExtractionResult, ExtractionUsage, StatusReportExtraction,
    StatusReportRequest,
)

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "status_report_extractor.md"


class ExtractionError(Exception):
    """A safe public error; never store provider messages or credentials."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def extract_status_report(text: str) -> ExtractionResult:
    # Also validate direct service callers, before any paid request.
    StatusReportRequest(text=text)
    settings = get_openai_settings()
    api_key = settings.api_key.get_secret_value() if settings.api_key else None
    response = None
    http_status = None
    request_id = None
    if settings.api_key is None:
        log_failure(category="configuration", model=settings.model, api_key=None,
                    message="OPENAI_API_KEY is not configured.")
        raise ExtractionError("not_configured", "AI extraction requires OPENAI_API_KEY to be configured.")
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        log_failure(category="configuration", model=settings.model, api_key=api_key,
                    exception=exc, message="The extraction prompt is unavailable.")
        raise ExtractionError("unavailable", "The extraction prompt is unavailable.") from None

    try:
        with OpenAI(api_key=settings.api_key.get_secret_value(), timeout=60.0, max_retries=0) as client:
            # Wrap the same SDK parse call so headers survive parsing failures.
            raw_response = client.responses.with_raw_response.parse(
                model=settings.model,
                input=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
                text_format=StatusReportExtraction,
                max_output_tokens=12_000,
                store=False,
            )
            http_status = raw_response.status_code
            request_id = raw_response.headers.get("x-request-id")
            # An incomplete response can contain truncated JSON that the SDK
            # cannot parse. Identify that condition before parsing its output.
            envelope = raw_response.http_response.json()
            if isinstance(envelope, dict) and envelope.get("status") == "incomplete":
                details = envelope.get("incomplete_details") or {}
                log_failure(category="incomplete_response", model=settings.model, api_key=api_key,
                            message="Provider returned an incomplete response.",
                            http_status=http_status, request_id=request_id,
                            reason=details.get("reason") if isinstance(details, dict) else None)
                raise ExtractionError("invalid_output", "AI extraction did not return a complete structured result.")
            response = raw_response.parse()
        def output_failure(category: str, message: str, reason: str | None = None) -> None:
            log_failure(category=category, model=settings.model, api_key=api_key,
                        message=message, http_status=http_status, request_id=request_id,
                        reason=reason)
            raise ExtractionError("invalid_output", "AI extraction did not return a complete structured result.")

        if response.status == "incomplete":
            output_failure("incomplete_response", "Provider returned an incomplete response.",
                           getattr(response.incomplete_details, "reason", None))
        if any(getattr(part, "type", None) == "refusal"
               for item in response.output if item.type == "message" for part in item.content):
            # Refusal text can quote sensitive report content; log the condition only.
            output_failure("model_refusal", "Model refused the extraction request.")
        if response.status != "completed":
            output_failure("response_not_completed", "Provider response did not complete.", response.status)
        if response.output_parsed is None:
            output_failure("missing_parsed_output", "Completed response has no parsed extraction.")
        extraction = StatusReportExtraction.model_validate(response.output_parsed)
        # Structured output ensures shape, not grounding. Reject invented quotations.
        normalized_text = " ".join(text.split())
        for field in OBSERVATION_FIELDS:
            for observation in getattr(extraction, field):
                snippet = " ".join(observation.source_snippet.split())
                if not snippet or snippet not in normalized_text:
                    log_failure(category="untraceable_excerpt", model=settings.model, api_key=api_key,
                                message="Extracted source excerpt does not occur in the submitted report.",
                                http_status=http_status, request_id=request_id)
                    raise ExtractionError("invalid_output", "AI extraction returned an untraceable source excerpt.")
        extraction = normalize_evidence(extraction, text)
        usage = response.usage
        return ExtractionResult(
            extraction=extraction,
            usage=ExtractionUsage(
                model=response.model,
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
                total_tokens=usage.total_tokens if usage else None,
            ),
        )
    except APIError as exc:
        # Order matters: timeouts inherit from APIConnectionError.
        category = "provider_error"
        for error_class, label in (
            (APITimeoutError, "timeout"),
            (AuthenticationError, "authentication"),
            (PermissionDeniedError, "permission_denied"),
            (BadRequestError, "bad_request"),
            (RateLimitError, "rate_limit"),
            (APIConnectionError, "connection"),
            (APIResponseValidationError, "structured_output_validation"),
        ):
            if isinstance(exc, error_class):
                category = label
                break
        if isinstance(exc, RateLimitError) and (exc.code == "insufficient_quota" or exc.type == "insufficient_quota"):
            category = "insufficient_quota"
        # Never stringify an SDK exception: it can include bodies and credentials.
        body = exc.body if isinstance(exc.body, dict) else {}
        message = body.get("message")
        if not isinstance(message, str):
            message = "OpenAI request failed; no safe provider message available."
        http_response = getattr(exc, "response", None)
        request_id = getattr(exc, "request_id", None)
        if request_id is None and http_response is not None:
            request_id = http_response.headers.get("x-request-id")
        log_failure(category=category, model=settings.model, api_key=api_key,
                    exception=exc, http_status=getattr(exc, "status_code", None),
                    error_code=exc.code, error_type=exc.type, message=message,
                    request_id=request_id)
        if isinstance(exc, APITimeoutError):
            raise ExtractionError("timeout", "AI extraction timed out. Try again later.") from None
        raise ExtractionError("upstream_failure", "AI extraction provider request failed. Check configuration and try again.") from None
    except (ValidationError, ValueError) as exc:
        # Error input, context and even custom messages may contain report text.
        error_types = sorted({error["type"] for error in exc.errors(
            include_input=False, include_context=False, include_url=False
        )}) if isinstance(exc, ValidationError) else None
        log_failure(category="structured_output_validation", model=settings.model, api_key=api_key,
                    exception=exc, message="Structured output failed parsing or validation.",
                    http_status=http_status, request_id=request_id,
                    validation_error_types=error_types)
        raise ExtractionError("invalid_output", "AI extraction returned invalid structured evidence.") from None
