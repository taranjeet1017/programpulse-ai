"""One extraction request followed by deterministic evidence assurance."""
from pathlib import Path

from app.models.program_assessment import ProgramAssessment
from app.ingestion.models import SourceLocation
from app.models.input_evidence import ProjectEvidence
from app.services.assessment_output import build_assessment
from app.services.evidence_adapters import adapt_ai, adapt_structured
from app.services.evidence_consolidation import consolidate
from app.services.evidence_normalizer import normalize_evidence
from app.services.health_rules import calculate_normalized_assessment
from app.services.openai_evidence_extractor import ExtractionError, extract_status_report
from app.services.sample_loader import SAMPLE_DIRECTORY, load_sample_evidence


def assess_ai_sample(directory: Path = SAMPLE_DIRECTORY) -> ProgramAssessment:
    # Validate all local sources before incurring the cost of extraction.
    bundle = load_sample_evidence(directory)
    return assess_evidence(bundle)


def assess_evidence(bundle: ProjectEvidence, source_names: dict[str, str] | None = None,
                    source_locations: dict[str, SourceLocation] | None = None) -> ProgramAssessment:
    """Shared pipeline for validated local or uploaded evidence; one extraction."""
    extracted = extract_status_report(bundle.weekly_status.narrative)
    normalized = normalize_evidence(extracted.extraction, bundle.weekly_status.narrative)
    if normalized.project_name is not None and normalized.project_name != bundle.weekly_status.project:
        raise ExtractionError("invalid_output", "Extracted project identity does not match the evidence snapshot.")
    if normalized.reporting_date is not None and normalized.reporting_date != bundle.weekly_status.reporting_date:
        raise ExtractionError("invalid_output", "Extracted reporting date does not match the evidence snapshot.")
    if normalized.reported_health is not None and normalized.reported_health != bundle.weekly_status.reported_health:
        raise ExtractionError("invalid_output", "Extracted reported health does not match the explicit report header.")
    records = adapt_structured(bundle) + adapt_ai(normalized, bundle)
    if source_names:
        for record in records:
            canonical = record.source_name
            location = (source_locations or {}).get(record.source_reference)
            if location:
                record.source_name = location.filename
                record.source_reference = location.reference()
                record.source_section = location.reference().partition(" | ")[2] or None
                record.metadata["source_location"] = location.model_dump()
                continue
            if canonical in source_names:
                record.source_name = source_names[canonical]
                if record.source_reference.startswith(canonical):
                    record.source_reference = record.source_name + record.source_reference[len(canonical):]
    consolidated = consolidate(records)
    assessment = calculate_normalized_assessment(bundle.weekly_status, consolidated.evidence)
    return build_assessment(assessment, consolidated, extracted.usage, bundle.weekly_status.reporting_date)
