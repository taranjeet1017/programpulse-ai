from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ProgramPulse AI"}


def test_demo_assessment(client: TestClient) -> None:
    response = client.get("/api/v1/demo-assessment")
    assert response.status_code == 200
    assessment = response.json()
    assert assessment["assessment_version"] == "1.0"
    assert assessment["project"] == "AssessPro Modernization & Feature Expansion"
    assert assessment["assessed_health"] == "AMBER"
    assert assessment["reported_health"] == "GREEN"
    assert assessment["status_conflict"] is True
    assert assessment["confidence"] == "HIGH"
    assert assessment["leadership_attention_required"] is True
    assert assessment["health_dimensions"] == {
        "schedule": "AMBER",
        "scope": "AMBER",
        "quality": "AMBER",
        "dependencies": "RED",
        "actions": "AMBER",
        "governance": "AMBER",
    }
    assert len(assessment["evidence"]) >= 3
    assert len(assessment["recommended_leadership_actions"]) == 3
