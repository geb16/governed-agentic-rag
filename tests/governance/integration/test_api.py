from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import governed_main as governed_main_module
from app.core.config import Settings
from app.governance.experiments import manifest as manifest_module
from app.governance.security import GovernanceSecuritySettings
from app.governance.version import BASELINE_CONTROL_SHA256
from app.governed_main import create_governed_app
from app.rag.retriever import KnowledgeRetriever
from tests.governance.support import (
    ScriptedGovernanceModel,
    build_governed_workflow,
    material_refund_model,
)


def test_governed_api_startup_invocation_status_and_audit(settings) -> None:
    app = create_governed_app(settings)
    with TestClient(app) as client:
        workflow = build_governed_workflow(
            settings=settings,
            retriever=app.state.retriever,
            repository=app.state.repository,
            model=ScriptedGovernanceModel(),
        )
        app.state.governed_workflow = workflow
        app.state.agent = workflow

        ready = client.get("/api/v1/health/ready")
        invoked = client.post(
            "/api/v1/governed/invoke",
            json={
                "requester_id": "api-user",
                "case_id": "case_default",
                "query": "Explain the normal support escalation policy",
            },
        )

        assert ready.status_code == 200
        assert invoked.status_code == 200
        body = invoked.json()
        assert body["status"] == "completed"
        assert body["current_stage"] == "final_response_audit"
        assert body["audit_event_count"] > 0
        assert invoked.headers["cache-control"] == "no-store"

        status_response = client.get(f"/api/v1/governed/{body['workflow_id']}")
        summary_response = client.get(f"/api/v1/governed/{body['workflow_id']}/summary")
        trace_response = client.get(f"/api/v1/governed/{body['workflow_id']}/audit")
        assert status_response.status_code == 200
        assert summary_response.status_code == 200
        assert summary_response.json()["workflow_id"] == body["workflow_id"]
        assert trace_response.status_code == 200
        assert trace_response.json()["chain_valid"] is True


@pytest.mark.parametrize(
    "endpoint",
    (
        "/api/v1/governed/wf_missing_workflow",
        "/api/v1/governed/wf_missing_workflow/summary",
        "/api/v1/governed/wf_missing_workflow/audit",
    ),
)
def test_governed_api_maps_unknown_workflow_reads_to_not_found(settings, endpoint: str) -> None:
    """Map every read representation of an unknown workflow to HTTP 404."""

    app = create_governed_app(settings)
    with TestClient(app) as client:
        workflow = build_governed_workflow(
            settings=settings,
            retriever=app.state.retriever,
            repository=app.state.repository,
            model=ScriptedGovernanceModel(),
        )
        app.state.governed_workflow = workflow

        response = client.get(endpoint)

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"


def test_governed_api_maps_unknown_case_to_not_found(settings) -> None:
    """Expose an unknown synthetic case as a stable HTTP 404 contract."""

    app = create_governed_app(settings)
    with TestClient(app) as client:
        workflow = build_governed_workflow(
            settings=settings,
            retriever=app.state.retriever,
            repository=app.state.repository,
            model=ScriptedGovernanceModel(),
        )
        app.state.governed_workflow = workflow

        response = client.post(
            "/api/v1/governed/invoke",
            json={
                "requester_id": "api-user",
                "case_id": "case_missing",
                "query": "Explain the support policy",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Synthetic case not found"


def test_governed_api_maps_unknown_approval_workflow_to_not_found(settings) -> None:
    """Return HTTP 404 before attempting a decision for an unknown workflow."""

    app = create_governed_app(
        settings,
        GovernanceSecuritySettings(approval_roles=["finance_manager"]),
    )
    with TestClient(app) as client:
        workflow = build_governed_workflow(
            settings=settings,
            retriever=app.state.retriever,
            repository=app.state.repository,
            model=ScriptedGovernanceModel(),
        )
        app.state.governed_workflow = workflow

        response = client.post(
            "/api/v1/governed/wf_missing_workflow/approval",
            json={
                "role": "finance_manager",
                "approved": True,
                "proposal_digest": "0" * 64,
                "expected_state_version": 1,
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"


def test_governed_api_replays_identical_request_id_and_rejects_drift(settings) -> None:
    """Make request identifiers idempotent while rejecting changed replay content."""

    app = create_governed_app(settings)
    with TestClient(app) as client:
        model = ScriptedGovernanceModel()
        workflow = build_governed_workflow(
            settings=settings,
            retriever=app.state.retriever,
            repository=app.state.repository,
            model=model,
        )
        app.state.governed_workflow = workflow
        payload = {
            "request_id": "req_idempotent_api",
            "requester_id": "api-user",
            "case_id": "case_default",
            "query": "Explain the normal support escalation policy",
        }

        created = client.post("/api/v1/governed/invoke", json=payload)
        calls_after_creation = list(model.calls)
        replayed = client.post("/api/v1/governed/invoke", json=payload)
        conflict = client.post(
            "/api/v1/governed/invoke",
            json={**payload, "query": "Explain a different policy"},
        )

    assert created.status_code == replayed.status_code == 200
    assert replayed.json()["workflow_id"] == created.json()["workflow_id"]
    assert replayed.json()["state_version"] == created.json()["state_version"]
    assert replayed.json()["audit_event_count"] == created.json()["audit_event_count"]
    assert model.calls == calls_after_creation
    assert conflict.status_code == 409
    assert "already bound to different input" in conflict.json()["detail"]


def test_governed_api_reports_unavailable_without_a_model(settings) -> None:
    """Expose liveness while failing readiness and invocation when no model is configured."""

    app = create_governed_app(settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/health/ready").status_code == 503
        assert (
            client.post(
                "/api/v1/governed/invoke",
                json={"requester_id": "tester", "query": "Explain policy"},
            ).status_code
            == 503
        )


def test_production_disables_interactive_api_documentation(settings) -> None:
    """Remove schema-discovery endpoints from the production attack surface."""

    production = Settings(
        environment="production",
        execution_profile="development",
        api_key=SecretStr("production-api-key"),
        openai_api_key=SecretStr("production-provider-key"),
        safety_identifier_secret=SecretStr("production-identity-secret"),
        retrieval_backend="lexical",
        knowledge_base_dir=settings.knowledge_base_dir,
        synthetic_database_path=settings.synthetic_database_path,
    )
    security = GovernanceSecuritySettings(
        approval_roles=["finance_manager"],
        audit_integrity_key=SecretStr("a" * 32),
    )

    app = create_governed_app(production, security)

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_experiment_startup_automatically_records_the_governed_manifest(
    settings,
    retriever: KnowledgeRetriever,
    tmp_path,
    monkeypatch,
) -> None:
    """Make experiment identity an application-startup invariant, not a manual task."""

    experiment = Settings(
        environment="test",
        execution_profile="experiment",
        openai_api_key=SecretStr("provider-test-key"),
        safety_identifier_secret=SecretStr("identity-test-secret"),
        retrieval_backend="qdrant",
        qdrant_url="https://qdrant.invalid",
        experiment_run_id="run_governed_startup",
        experiment_manifest_dir=tmp_path,
        knowledge_base_dir=settings.knowledge_base_dir,
        synthetic_database_path=tmp_path / "governed-startup.db",
    )
    security = GovernanceSecuritySettings(audit_integrity_key=SecretStr("a" * 32))
    monkeypatch.setattr(governed_main_module, "KnowledgeRetriever", lambda _: retriever)
    monkeypatch.setattr(
        governed_main_module,
        "OpenAIGovernanceModel",
        lambda _: ScriptedGovernanceModel(),
    )
    monkeypatch.setattr(
        manifest_module,
        "verify_phase3_control_freeze",
        lambda: BASELINE_CONTROL_SHA256,
    )

    app = create_governed_app(experiment, security)
    with TestClient(app):
        manifest = app.state.experiment_manifest

    assert manifest is not None
    assert manifest.run_id == "run_governed_startup"
    assert (tmp_path / "run_governed_startup" / "governed-manifest.json").is_file()


def test_approval_api_uses_server_bound_identity_and_roles(settings) -> None:
    """Reject caller-claimed identity and roles not granted to the API principal."""

    app = create_governed_app(
        settings,
        GovernanceSecuritySettings(
            approval_principal_id="configured-reviewer",
            approval_roles=["support_supervisor"],
        ),
    )
    with TestClient(app) as client:
        workflow = build_governed_workflow(
            settings=settings,
            retriever=app.state.retriever,
            repository=app.state.repository,
            model=material_refund_model(),
        )
        app.state.governed_workflow = workflow
        pending = client.post(
            "/api/v1/governed/invoke",
            json={
                "requester_id": "api-user",
                "case_id": "case_default",
                "query": "Issue a GBP 750 refund on ticket TKT-1003 with all details",
            },
        ).json()
        approval = {
            "role": "finance_manager",
            "approved": True,
            "proposal_digest": pending["approval_route"]["proposal_digest"],
            "expected_state_version": pending["state_version"],
        }

        forbidden = client.post(
            f"/api/v1/governed/{pending['workflow_id']}/approval",
            json=approval,
        )
        caller_claim = client.post(
            f"/api/v1/governed/{pending['workflow_id']}/approval",
            json={**approval, "approver_id": "self-claimed-finance-manager"},
        )
        app.state.governance_security = GovernanceSecuritySettings(
            approval_principal_id="configured-reviewer",
            approval_roles=["finance_manager"],
        )
        conflict = client.post(
            f"/api/v1/governed/{pending['workflow_id']}/approval",
            json={**approval, "proposal_digest": "0" * 64},
        )
        authorized = client.post(
            f"/api/v1/governed/{pending['workflow_id']}/approval",
            json=approval,
        )

        assert forbidden.status_code == 403
        assert caller_claim.status_code == 422
        assert conflict.status_code == 409
        assert authorized.status_code == 200
        assert authorized.json()["status"] == "completed"
