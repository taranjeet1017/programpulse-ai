"""Validated source contracts for the sample evidence bundle."""
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.models.assessment import AssessmentModel, HealthStatus


class SourceSnapshot(AssessmentModel):
    project: str = Field(min_length=1)
    reporting_date: date


class WeeklyStatusReport(SourceSnapshot):
    reported_health: HealthStatus
    target_production_release: date
    narrative: str = Field(min_length=1)


class RaidItem(AssessmentModel):
    evidence_key: str | None = None
    id: str
    kind: Literal["dependency", "risk", "scope", "action"]
    title: str
    status: Literal["OPEN", "CLOSED"]
    due_date: date | None = None
    committed_resolution_date: date | None = None
    critical: bool = False
    material: bool
    important: bool
    escalated: bool
    release_blocker: bool
    impact_assessed: bool = True
    affects: list[str] = Field(default_factory=list)
    overdue_days_reported: int | None = Field(default=None, ge=0)


class RaidLog(SourceSnapshot):
    items: list[RaidItem]

    @model_validator(mode="after")
    def unique_ids(self) -> "RaidLog":
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("RAID IDs must be unique")
        return self


class Milestone(AssessmentModel):
    evidence_key: str | None = None
    id: str
    title: str
    baseline: date
    forecast: date | None
    critical_path: bool
    completed: bool


class MilestonePlan(SourceSnapshot):
    milestones: list[Milestone] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> "MilestonePlan":
        if len({item.id for item in self.milestones}) != len(self.milestones):
            raise ValueError("Milestone IDs must be unique")
        return self


TestState = Literal["NOT STARTED", "IN PROGRESS", "BLOCKED", "COMPLETED"]


class DefectSummary(SourceSnapshot):
    planned_tests: int = Field(gt=0)
    executed: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    blocked: int = Field(ge=0)
    test_execution_percent: float = Field(ge=0, le=100)
    sev1_open: int = Field(ge=0)
    sev2_open: int = Field(ge=0)
    sev2_reopened: int = Field(ge=0)
    scoring_sev2: int = Field(ge=0)
    regression_testing: TestState
    accessibility_testing: TestState
    proctoring_e2e_validation: TestState

    @model_validator(mode="after")
    def consistent_counts(self) -> "DefectSummary":
        if self.executed != self.passed + self.failed + self.blocked:
            raise ValueError("Executed must equal passed + failed + blocked in this sample convention")
        if self.executed > self.planned_tests:
            raise ValueError("Executed exceeds planned tests")
        if max(self.sev2_reopened, self.scoring_sev2) > self.sev2_open:
            raise ValueError("Sev-2 subsets exceed open Sev-2 count")
        if abs(self.test_execution_percent - 100 * self.executed / self.planned_tests) > 0.5:
            raise ValueError("Execution percentage does not match counts")
        return self


class ProjectEvidence(AssessmentModel):
    weekly_status: WeeklyStatusReport
    raid: RaidLog
    milestone_plan: MilestonePlan
    quality: DefectSummary

    @model_validator(mode="after")
    def consistent_snapshots(self) -> "ProjectEvidence":
        for source in (self.raid, self.milestone_plan, self.quality):
            if (source.project, source.reporting_date) != (self.weekly_status.project, self.weekly_status.reporting_date):
                raise ValueError("All evidence must describe the same project and reporting date")
        return self
