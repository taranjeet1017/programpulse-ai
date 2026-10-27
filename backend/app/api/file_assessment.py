"""Bounded, ephemeral multipart evidence assessment."""
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from starlette.responses import JSONResponse

from app.api.ai_extraction import ERROR_STATUS
from app.models.program_assessment import DashboardAssessment
from app.services.assessment_orchestrator import assess_evidence
from app.services.dashboard_assessment import summarize_assessment
from app.services.openai_evidence_extractor import ExtractionError
from app.ingestion.bundle_reader import ingest_uploads
from app.ingestion.models import IngestionError

router = APIRouter(tags=["Assessments"])
MAX_BODY_BYTES = 3_200_000
LABELS = {"status_report": "Weekly Status Report", "raid_log": "RAID Log",
          "milestone_plan": "Milestone Plan", "quality_summary": "Quality / Defect Summary"}


def invalid(field: str, code: str) -> HTTPException:
    # Closed error vocabulary; never echo uploaded contents or validation inputs.
    messages = {
        "extension": "has an unsupported file extension.", "empty": "is empty.",
        "size": "exceeds the file-size limit.", "encoding": "must use UTF-8 encoding.",
        "json": "is not valid JSON.", "schema": "does not match the expected structure.",
        "metadata": "requires valid Project, Reporting date, Reported overall health and Target production release headers.",
        "pdf_text": "contains insufficient machine-readable text. Scanned PDF support is not available in this version.",
        "encrypted": "is password-protected or encrypted and is not supported.",
        "malformed": "could not be read. Check that the file is valid and not encrypted.",
        "resource_limit": "exceeds the supported document complexity limits.",
        "macros": "contains unsupported macros.", "formulas": "contains formulas. Export values before uploading.",
        "missing_columns": "is missing required recognizable columns.",
        "ambiguous_columns": "has multiple columns mapping to the same field.",
        "quality_rows": "must contain exactly one summary metrics row.",
        "snapshot": "must match the report's project and reporting date.",
    }
    return HTTPException(422, detail={"code": "invalid_file", "field": field, "reason": code,
                                      "message": f"{LABELS[field]} {messages[code]}"})


class UploadBodyLimit:
    """Bound the body before the multipart parser can spool arbitrary input to disk."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/v1/ai/assess-files":
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_BODY_BYTES:
                return await JSONResponse(status_code=413, content={"detail": {"code": "upload_too_large"}})(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)


@router.post("/api/v1/ai/assess-files", response_model=DashboardAssessment)
def assess_files(
    response: Response,
    status_report: Annotated[UploadFile, File()],
    raid_log: Annotated[UploadFile, File()],
    milestone_plan: Annotated[UploadFile, File()],
    quality_summary: Annotated[UploadFile, File()],
) -> DashboardAssessment:
    """Ingest all four documents before making one paid extraction request."""
    response.headers["Cache-Control"] = "no-store"
    uploads = dict(status_report=status_report, raid_log=raid_log,
                   milestone_plan=milestone_plan, quality_summary=quality_summary)
    try:
        try:
            ingested = ingest_uploads(uploads)
        except IngestionError as exc:
            error = invalid(exc.field, exc.reason)
            if exc.mapping:
                error.detail["missing_required_fields"] = exc.mapping.missing_required_fields
                if exc.mapping.missing_required_fields:
                    error.detail["message"] += " Required: " + ", ".join(exc.mapping.missing_required_fields) + "."
            raise error from None
        try:
            completed = assess_evidence(ingested.bundle, source_names=ingested.names,
                                        source_locations=ingested.locations)
            return summarize_assessment(completed)
        except ExtractionError as exc:
            raise HTTPException(ERROR_STATUS[exc.code], detail={"code": exc.code}) from None
        except (ValueError, OSError):
            raise HTTPException(502, detail={"code": "invalid_output"}) from None
    finally:
        # Starlette also closes multipart uploads at request teardown; close eagerly.
        for upload in uploads.values():
            upload.file.close()
