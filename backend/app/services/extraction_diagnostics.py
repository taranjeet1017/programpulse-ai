"""Allowlisted, single-line diagnostics without raw exceptions or response bodies."""
import json
import logging
import os
import re

logger = logging.getLogger(__name__)
SENSITIVE_NAME = re.compile(r"key|token|secret|password|credential|authorization", re.I)
SENSITIVE_TEXT = re.compile(
    r"sk-[\w*-]+|bearer\s+|api[ _-]?key|password|secret|authorization|credential"
    r"|(?:access[_-]?token|token)\s*[:=]|://[^\s/]+@|eyJ[\w-]+\.eyJ", re.I
)


def safe_text(value: object, api_key: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    # Suppress the entire field when it might contain credentials. This also
    # avoids leaving revealing fragments of an authentication error behind.
    secrets = [api_key] if api_key else []
    secrets.extend(value for name, value in os.environ.items()
                   if SENSITIVE_NAME.search(name) and len(value) >= 4)
    if any(secret in value for secret in secrets) or (
        value != "invalid_api_key" and SENSITIVE_TEXT.search(value)
    ):
        return "[redacted sensitive diagnostic]"
    # JSON encoding below escapes control characters, preventing forged log lines.
    return value[:1000]


def log_failure(
    *, category: str, model: str, api_key: str | None, message: str,
    exception: Exception | None = None, http_status: int | None = None,
    error_code: object = None, error_type: object = None,
    request_id: object = None, reason: object = None,
    validation_error_types: list[str] | None = None,
) -> None:
    diagnostic = {
        "event": "openai_extraction_failure",
        "category": category,
        "exception_class": type(exception).__name__ if exception else None,
        "http_status": http_status,
        "error_code": safe_text(error_code, api_key),
        "error_type": safe_text(error_type, api_key),
        "message": safe_text(message, api_key),
        "request_id": safe_text(request_id, api_key),
        "model": safe_text(model, api_key),
        "reason": safe_text(reason, api_key),
        "validation_error_types": validation_error_types,
    }
    logger.warning("%s", json.dumps(diagnostic, ensure_ascii=True))
