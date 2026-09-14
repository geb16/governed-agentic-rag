"""Run one isolated, provider-backed smoke check of the Phase 4 HTTP boundary.

The check exercises application startup, health endpoints, governed invocation,
durable workflow state, and the keyed audit chain. It uses an ephemeral SQLite
database, the local lexical knowledge base, and the test execution profile, so it
cannot modify configured business data or create an experiment manifest.

``RAG_OPENAI_API_KEY`` must be configured. One workflow can make multiple provider
requests and incur usage. Deterministic behavior remains covered by the governance
test suite; this script verifies runtime composition and provider integration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory
from typing import TypeVar

from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import BaseModel, SecretStr, ValidationError

from app.audit.schemas import AUDIT_SCHEMA_VERSION, AuditTrace
from app.baseline.api.contracts import HealthResponse
from app.core.config import Settings, get_settings
from app.governance.contracts import GovernedResponse, WorkflowStage, WorkflowStatus
from app.governance.security import GovernanceSecuritySettings
from app.governed_main import create_governed_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class SmokeCheckError(RuntimeError):
    """Report an expected smoke-check failure without exposing configuration secrets."""


def _require(condition: bool, message: str) -> None:
    """Raise a readable failure when a smoke invariant is not satisfied."""

    if not condition:
        raise SmokeCheckError(message)


def _parse_response(
    response: Response,
    model: type[ResponseModel],
    *,
    operation: str,
) -> ResponseModel:
    """Validate an HTTP response status and deserialize its published contract."""

    if not response.is_success:
        detail = response.text[:500].replace("\n", " ")
        raise SmokeCheckError(f"{operation} returned HTTP {response.status_code}: {detail}")
    return model.model_validate(response.json())


def _isolated_settings(database_path: Path) -> Settings:
    """Copy provider settings while isolating storage, retrieval, and run artifacts."""

    configured = get_settings()
    if configured.openai_api_key is None:
        raise SmokeCheckError("RAG_OPENAI_API_KEY is required for the Phase 4 smoke check")

    knowledge_base_dir = configured.knowledge_base_dir
    if not knowledge_base_dir.is_absolute():
        knowledge_base_dir = PROJECT_ROOT / knowledge_base_dir
    _require(knowledge_base_dir.is_dir(), f"Knowledge base not found: {knowledge_base_dir}")

    return configured.model_copy(
        update={
            "environment": "test",
            "execution_profile": "test",
            "allowed_hosts": ["testserver"],
            "knowledge_base_dir": knowledge_base_dir,
            "retrieval_backend": "lexical",
            "synthetic_database_path": database_path,
        }
    )


def run_smoke_check() -> dict[str, object]:
    """Execute the isolated happy path and return a secret-free diagnostic summary."""

    with TemporaryDirectory(prefix="phase4-smoke-") as temporary_directory:
        settings = _isolated_settings(Path(temporary_directory) / "phase4-smoke.db")
        governance_security = GovernanceSecuritySettings(
            approval_principal_id="phase4-smoke-reviewer",
            approval_roles=[],
            audit_integrity_key=SecretStr(token_urlsafe(32)),
        )
        application = create_governed_app(settings, governance_security)
        api_prefix = settings.api_prefix.rstrip("/")
        headers = (
            {"X-API-Key": settings.api_key.get_secret_value()}
            if settings.api_key is not None
            else {}
        )

        with TestClient(application) as client:
            live = _parse_response(
                client.get(f"{api_prefix}/health/live"),
                HealthResponse,
                operation="Liveness check",
            )
            ready = _parse_response(
                client.get(f"{api_prefix}/health/ready"),
                HealthResponse,
                operation="Readiness check",
            )
            _require(live.status == "ok", f"Unexpected liveness status: {live.status}")
            _require(ready.status == "ready", f"Unexpected readiness status: {ready.status}")

            result = _parse_response(
                client.post(
                    f"{api_prefix}/governed/invoke",
                    headers=headers,
                    json={
                        "request_id": "req_phase4_smoke",
                        "case_id": "case_default",
                        "requester_id": "phase4_smoke_user",
                        "query": (
                            "According to the knowledge base, what approval is required "
                            "for a refund of 750 GBP? Do not perform the refund."
                        ),
                    },
                ),
                GovernedResponse,
                operation="Governed invocation",
            )
            _require(
                result.status == WorkflowStatus.COMPLETED,
                (
                    "Expected a completed read-only workflow, received "
                    f"{result.status.value} (error_code={result.error_code or 'none'})"
                ),
            )
            _require(
                result.current_stage == WorkflowStage.FINAL_RESPONSE_AUDIT,
                f"Unexpected terminal stage: {result.current_stage.value}",
            )
            _require(bool(result.answer), "Completed workflow returned no answer")
            _require(bool(result.evidence), "Completed workflow returned no retrieved evidence")

            trace = _parse_response(
                client.get(
                    f"{api_prefix}/governed/{result.workflow_id}/audit",
                    headers=headers,
                ),
                AuditTrace,
                operation="Audit trace retrieval",
            )
            _require(trace.workflow_id == result.workflow_id, "Audit workflow identifier mismatch")
            _require(trace.chain_valid, "Governed audit chain verification failed")
            _require(bool(trace.events), "Governed audit trace is empty")
            _require(
                len(trace.events) == result.audit_event_count,
                "Response and persisted audit event counts differ",
            )
            _require(
                all(event.schema_version == AUDIT_SCHEMA_VERSION for event in trace.events),
                "Audit trace contains an unexpected schema version",
            )

        return {
            "service": live.service,
            "version": live.version,
            "workflow_id": result.workflow_id,
            "status": result.status.value,
            "current_stage": result.current_stage.value,
            "audit_schema_version": AUDIT_SCHEMA_VERSION,
            "audit_event_count": result.audit_event_count,
            "audit_chain_valid": trace.chain_valid,
            "retrieval_backend": result.retrieval_backend,
            "model": result.model,
        }


def main() -> int:
    """Print the smoke summary and return a shell-compatible exit status."""

    try:
        report = run_smoke_check()
    except (SmokeCheckError, ValidationError) as exc:
        print(f"Phase 4 smoke check failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
