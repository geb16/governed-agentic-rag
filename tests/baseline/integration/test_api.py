"""HTTP boundary contracts for authenticated baseline invocation."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.baseline.api.dependencies import get_agent
from app.baseline_main import create_app
from app.core.config import Settings
from app.domain.model import AgentDraft, ModelTurn
from app.rag.retriever import KnowledgeRetriever
from tests.baseline.support import ScriptedModel, build_agent


def test_invoke_endpoint_enforces_api_key(settings: Settings) -> None:
    """Reject a missing API key while accepting the configured credential."""
    protected_settings = settings.model_copy(update={"api_key": SecretStr("test-inbound-key")})
    retriever = KnowledgeRetriever(protected_settings)
    model = ScriptedModel(
        [
            ModelTurn(
                final=AgentDraft(
                    answer="The available knowledge does not cover that request.",
                    cited_chunk_ids=[],
                    grounded=False,
                )
            )
        ]
    )
    agent = build_agent(protected_settings, retriever, model)
    app = create_app(protected_settings)
    app.dependency_overrides[get_agent] = lambda: agent

    with TestClient(app) as client:
        unauthorized = client.post(
            "/api/v1/baseline/invoke",
            json={
                "requester_id": "pilot_user",
                "query": "What information is available?",
            },
        )
        authorized = client.post(
            "/api/v1/baseline/invoke",
            headers={"X-API-Key": "test-inbound-key"},
            json={
                "requester_id": "pilot_user",
                "query": "What information is available?",
            },
        )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["status"] == "completed"


def test_request_schema_rejects_extra_fields(settings: Settings) -> None:
    """Reject undeclared request fields before invoking the application service."""
    app = create_app(settings)
    app.dependency_overrides[get_agent] = lambda: object()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/baseline/invoke",
            json={
                "requester_id": "pilot_user",
                "query": "What information is available?",
                "admin_override": True,
            },
        )

    assert response.status_code == 422
