import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_dashboard_origin_allowed(origin: str) -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "access-control-allow-credentials" not in response.headers
        preflight = client.options("/api/v1/demo-ai-assessment/summary", headers={
            "Origin": origin, "Access-Control-Request-Method": "GET",
        })
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == origin


def test_unapproved_origin_not_allowed() -> None:
    with TestClient(app) as client:
        response = client.options("/api/v1/demo-ai-assessment/summary", headers={
            "Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET",
        })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
