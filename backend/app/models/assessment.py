"""Typed contracts for delivery assurance assessments."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(StrEnum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class Confidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssessmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthDimensions(AssessmentModel):
    schedule: HealthStatus
    scope: HealthStatus
    quality: HealthStatus
    dependencies: HealthStatus
    actions: HealthStatus
    governance: HealthStatus


class Evidence(AssessmentModel):
    description: str = Field(min_length=1)
    dimension: Literal["schedule", "scope", "quality", "dependencies", "actions", "governance"] | None = None
    references: list[str] = Field(default_factory=list)


class LeadershipAction(AssessmentModel):
    description: str = Field(min_length=1)


class Assessment(AssessmentModel):
    assessment_version: Literal["1.0"] = "1.0"
    project: str = Field(min_length=1)
    reported_health: HealthStatus
    assessed_health: HealthStatus
    status_conflict: bool
    confidence: Confidence
    leadership_attention_required: bool
    health_dimensions: HealthDimensions
    evidence: list[Evidence] = Field(min_length=1)
    recommended_leadership_actions: list[LeadershipAction] = Field(default_factory=list)
