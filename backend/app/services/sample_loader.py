"""Load the four local evidence files; never substitute a canned assessment."""
from pathlib import Path

from app.models.input_evidence import (
    DefectSummary, MilestonePlan, ProjectEvidence, RaidLog, WeeklyStatusReport,
)

SAMPLE_DIRECTORY = Path(__file__).resolve().parents[3] / "sample_data" / "assesspro"
# services -> app -> backend -> project root is parents[3].


def load_sample_evidence(directory: Path = SAMPLE_DIRECTORY) -> ProjectEvidence:
    report = (directory / "weekly_status_report.md").read_text(encoding="utf-8")
    return ProjectEvidence(
        weekly_status=parse_status_report(report),
        raid=RaidLog.model_validate_json((directory / "raid_log.json").read_text(encoding="utf-8")),
        milestone_plan=MilestonePlan.model_validate_json((directory / "milestone_plan.json").read_text(encoding="utf-8")),
        quality=DefectSummary.model_validate_json((directory / "defect_summary.json").read_text(encoding="utf-8")),
    )


def parse_status_report(report: str) -> WeeklyStatusReport:
    """Parse explicit snapshot headers without asking AI to invent metadata."""
    labels = {
        "Project": "project",
        "Reporting date": "reporting_date",
        "Reported overall health": "reported_health",
        "Target production release": "target_production_release",
    }
    metadata: dict[str, str] = {}
    for line in report.splitlines():
        label, separator, value = line.partition(":")
        if separator and label in labels:
            key = labels[label]
            if key in metadata:
                raise ValueError(f"Duplicate weekly report metadata: {label}")
            metadata[key] = value.strip()
    return WeeklyStatusReport.model_validate({**metadata, "narrative": report})
