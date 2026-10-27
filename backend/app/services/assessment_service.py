"""Orchestrate validated evidence loading and deterministic assessment."""
from pathlib import Path

from app.models.assessment import Assessment
from app.services.health_rules import calculate_assessment
from app.services.sample_loader import SAMPLE_DIRECTORY, load_sample_evidence


def assess_sample(directory: Path = SAMPLE_DIRECTORY) -> Assessment:
    return calculate_assessment(load_sample_evidence(directory))
