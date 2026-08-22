"""Application lifespan, liveness, and readiness endpoint contracts."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.baseline_main import create_app
from app.core.config import Settings


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


def test_production_disables_interactive_api_documentation(settings: Settings) -> None:
    """Do not publish OpenAPI or interactive documentation in production."""
    production_settings = Settings(
        environment="production",
        execution_profile="development",
        api_key=SecretStr("inbound-key"),
        openai_api_key=SecretStr("provider-key"),
        safety_identifier_secret=SecretStr("safety-identifier-key"),
        allowed_hosts=["service.example.test"],
        knowledge_base_dir=settings.knowledge_base_dir,
        synthetic_database_path=settings.synthetic_database_path,
    )

    app = create_app(production_settings)

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
