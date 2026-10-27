"""HTTP entry point for the ProgramPulse AI prototype."""

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.ai_extraction import router as ai_extraction_router
from app.api.file_assessment import router as file_router, UploadBodyLimit
from app.models.assessment import Assessment
from app.services.assessment_service import assess_sample

app = FastAPI(
    title="ProgramPulse AI",
    description="Agentic Delivery & Governance Platform — delivery assurance prototype.",
    version="1.0.0",
)

app.add_middleware(UploadBodyLimit)

# Explicit local dashboard origins. No credentials or wildcard origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)
app.include_router(ai_extraction_router)
app.include_router(file_router)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["ProgramPulse AI"] = "ProgramPulse AI"


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/v1/demo-assessment", response_model=Assessment, tags=["Assessments"])
def demo_assessment() -> Assessment:
    """Assess the current local evidence snapshot using deterministic rules."""
    return assess_sample()
