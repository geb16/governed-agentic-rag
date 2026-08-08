"""Application lifespan, liveness, and readiness endpoint contracts."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_application_startup_and_liveness(settings) -> None:
    """Initialize the application lifespan and report process liveness."""
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_reports_missing_model_configuration(settings) -> None:
    """Report 503 readiness when no model-backed baseline agent exists."""
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
