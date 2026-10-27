"""AI-only endpoints with safe errors and explicit usage visibility."""
from fastapi import APIRouter, HTTPException, Response
from pydantic import ValidationError

from app.models.program_assessment import DashboardAssessment, ProgramAssessment
from app.services.dashboard_assessment import summarize_assessment
from app.services.assessment_orchestrator import assess_ai_sample
from app.models.extraction import ExtractionResult, StatusReportExtraction, StatusReportRequest
from app.services.openai_evidence_extractor import ExtractionError, extract_status_report
from app.services.sample_loader import SAMPLE_DIRECTORY

router = APIRouter(tags=["AI extraction"])
ERROR_STATUS = {"not_configured": 503, "unavailable": 503, "timeout": 504,
                "upstream_failure": 502, "invalid_output": 502}
ERROR_RESPONSES = {
    502: {"description": "Provider failure, refusal, incomplete or invalid extraction."},
    503: {"description": "AI extraction not configured or local resources unavailable."},
    504: {"description": "Provider request timed out."},
}


def run_extraction(text: str) -> ExtractionResult:
    try:
        return extract_status_report(text)
    except ExtractionError as exc:
        raise HTTPException(status_code=ERROR_STATUS[exc.code],
                            detail={"code": exc.code, "message": str(exc)}) from None


@router.post("/api/v1/ai/extract-status-report", response_model=StatusReportExtraction,
             responses=ERROR_RESPONSES, response_model_exclude_unset=True)
def extract_report(request: StatusReportRequest, response: Response) -> StatusReportExtraction:
    """Extract evidence with OpenAI. Consumes API credits; does not calculate health."""
    response.headers["Cache-Control"] = "no-store"
    return run_extraction(request.text).extraction


@router.get("/api/v1/demo-ai-extraction", response_model=ExtractionResult,
            responses=ERROR_RESPONSES, response_model_exclude_unset=True)
def demo_ai_extraction(response: Response) -> ExtractionResult:
    """Send the sample report to OpenAI on every call; return evidence and token usage."""
    response.headers["Cache-Control"] = "no-store"
    try:
        text = (SAMPLE_DIRECTORY / "weekly_status_report.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise HTTPException(status_code=503, detail={
            "code": "unavailable", "message": "The sample status report is unavailable."
        }) from None
    # Validate the local file with the same constraints as a submitted report.
    try:
        StatusReportRequest(text=text)
    except ValidationError:
        raise HTTPException(status_code=503, detail={
            "code": "unavailable", "message": "The sample status report is invalid."
        }) from None
    return run_extraction(text)


@router.get("/api/v1/demo-ai-assessment", response_model=ProgramAssessment,
            responses=ERROR_RESPONSES)
def demo_ai_assessment(response: Response) -> ProgramAssessment:
    """One paid extraction followed by deterministic, traceable governance assessment."""
    response.headers["Cache-Control"] = "no-store"
    return run_assessment()


def run_assessment() -> ProgramAssessment:
    try:
        return assess_ai_sample()
    except ExtractionError as exc:
        raise HTTPException(status_code=ERROR_STATUS[exc.code],
                            detail={"code": exc.code, "message": str(exc)}) from None
    except (OSError, UnicodeError, ValueError):
        raise HTTPException(status_code=503, detail={
            "code": "unavailable", "message": "The local assessment evidence is unavailable or invalid."
        }) from None


@router.get("/api/v1/demo-ai-assessment/summary", response_model=DashboardAssessment,
            responses=ERROR_RESPONSES)
def demo_ai_assessment_summary(response: Response) -> DashboardAssessment:
    """One assessment request, projected into a compact dashboard response."""
    response.headers["Cache-Control"] = "no-store"
    completed = run_assessment()
    return summarize_assessment(completed)
