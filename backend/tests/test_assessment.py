import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.assessment import HealthStatus
from app.models.input_evidence import ProjectEvidence
from app.services.assessment_service import assess_sample
from app.services.health_rules import calculate_assessment
from app.services.sample_loader import SAMPLE_DIRECTORY, load_sample_evidence


@pytest.fixture
def sample_directory(tmp_path: Path) -> Path:
    shutil.copytree(SAMPLE_DIRECTORY, tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_loaded_scenario() -> None:
    bundle = load_sample_evidence()
    result = calculate_assessment(bundle)
    assert result.reported_health == "GREEN"
    assert result.assessed_health == "AMBER"
    assert result.status_conflict is True
    assert result.health_dimensions.dependencies == "RED"
    assert result.health_dimensions.quality == "AMBER"
    assert result.health_dimensions.schedule == "AMBER"
    assert bundle.quality.executed == 842
    assert "No immediate escalation" in bundle.weekly_status.narrative
    assert any("9 days overdue" in item.description for item in result.evidence)


def test_every_dimension_has_resolvable_references() -> None:
    result = assess_sample()
    assert {item.dimension for item in result.evidence} == set(result.health_dimensions.model_dump())
    for item in result.evidence:
        assert item.references
        for ref in item.references:
            filename, _, pointer = ref.partition("#")
            data = json.loads((SAMPLE_DIRECTORY / filename).read_text())
            for key in pointer.strip("/").split("/") if pointer else []:
                data = data[int(key)] if isinstance(data, list) else data[key]
            assert data is not None


def test_api_uses_changed_files(sample_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main
    monkeypatch.setattr(main, "assess_sample", lambda: assess_sample(sample_directory))
    with TestClient(app) as client:
        assert client.get("/api/v1/demo-assessment").json()["assessed_health"] == "AMBER"
        raid_path = sample_directory / "raid_log.json"
        raid = json.loads(raid_path.read_text())
        raid["items"][0]["release_blocker"] = True
        raid_path.write_text(json.dumps(raid))
        response = client.get("/api/v1/demo-assessment")
        assert response.status_code == 200
        assert response.json()["assessed_health"] == "RED"
        report_path = sample_directory / "weekly_status_report.md"
        report_path.write_text(report_path.read_text().replace("Reported overall health: GREEN", "Reported overall health: RED"))
        result = client.get("/api/v1/demo-assessment").json()
        assert result["reported_health"] == "RED"
        assert result["status_conflict"] is False


def clean_bundle() -> ProjectEvidence:
    bundle = load_sample_evidence()
    for item in bundle.raid.items:
        item.status = "CLOSED"
    for milestone in bundle.milestone_plan.milestones:
        milestone.forecast = milestone.baseline
        milestone.completed = True
    quality = bundle.quality
    quality.sev1_open = quality.sev2_open = quality.sev2_reopened = quality.scoring_sev2 = 0
    quality.regression_testing = quality.accessibility_testing = quality.proctoring_e2e_validation = "COMPLETED"
    return bundle


def test_resolved_evidence_returns_green() -> None:
    result = calculate_assessment(clean_bundle())
    assert set(result.health_dimensions.model_dump().values()) == {HealthStatus.GREEN}
    assert result.assessed_health == "GREEN"
    assert result.status_conflict is False
    assert result.leadership_attention_required is False
    assert result.recommended_leadership_actions == []


@pytest.mark.parametrize("days,committed,critical,expected", [
    (1, False, True, "RED"), (0, False, True, "GREEN"),
    (1, True, True, "GREEN"), (1, False, False, "GREEN"),
])
def test_dependency_rule(days: int, committed: bool, critical: bool, expected: str) -> None:
    bundle = clean_bundle()
    item = bundle.raid.items[0]
    item.status = "OPEN"
    item.escalated = True
    item.critical = critical
    item.due_date = bundle.weekly_status.reporting_date - timedelta(days=days)
    item.committed_resolution_date = bundle.weekly_status.reporting_date if committed else None
    result = calculate_assessment(bundle)
    assert result.health_dimensions.dependencies == expected
    assert result.assessed_health == ("AMBER" if expected == "RED" else "GREEN")


@pytest.mark.parametrize("slip,critical,expected", [(2, True, "GREEN"), (3, True, "AMBER"), (7, False, "GREEN")])
def test_schedule_threshold(slip: int, critical: bool, expected: str) -> None:
    bundle = clean_bundle()
    milestone = bundle.milestone_plan.milestones[1]
    milestone.completed = False
    milestone.critical_path = critical
    milestone.forecast = milestone.baseline + timedelta(days=slip)
    assert calculate_assessment(bundle).health_dimensions.schedule == expected


@pytest.mark.parametrize("field,value,expected", [
    ("sev2_open", 4, "GREEN"), ("sev2_open", 5, "AMBER"),
    ("sev2_reopened", 1, "AMBER"), ("regression_testing", "NOT STARTED", "AMBER"),
])
def test_independent_quality_signals(field: str, value: object, expected: str) -> None:
    bundle = clean_bundle()
    setattr(bundle.quality, field, value)
    if field == "sev2_reopened":
        bundle.quality.sev2_open = 1
    assert calculate_assessment(bundle).health_dimensions.quality == expected


@pytest.mark.parametrize("kind,dimension", [("scope", "scope"), ("action", "actions"), ("risk", "governance")])
def test_other_rules(kind: str, dimension: str) -> None:
    bundle = clean_bundle()
    item = next(item for item in bundle.raid.items if item.kind == kind)
    item.status = "OPEN"
    assert getattr(calculate_assessment(bundle).health_dimensions, dimension) == "AMBER"
    if kind == "scope":
        item.impact_assessed = True
    elif kind == "action":
        item.due_date = bundle.weekly_status.reporting_date
    else:
        item.escalated = True
    assert getattr(calculate_assessment(bundle).health_dimensions, dimension) == "GREEN"


@pytest.mark.parametrize("filename", ["weekly_status_report.md", "raid_log.json", "milestone_plan.json", "defect_summary.json"])
def test_missing_source_fails(sample_directory: Path, filename: str) -> None:
    (sample_directory / filename).unlink()
    with pytest.raises(FileNotFoundError):
        assess_sample(sample_directory)


@pytest.mark.parametrize("change", [{"sev2_open": -1}, {"executed": 999}, {"reporting_date": "2026-09-19"}])
def test_invalid_evidence_rejected(sample_directory: Path, change: dict[str, object]) -> None:
    path = sample_directory / "defect_summary.json"
    data = json.loads(path.read_text())
    data.update(change)
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        assess_sample(sample_directory)
