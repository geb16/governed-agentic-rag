"""Create the Phase 4 governed FastAPI application and its process-level instance.

Extends the frozen Phase 3 substrate with workflow and audit persistence and
the governed-workflow routes; composition details live on create_governed_app.
Core:
    - create_governed_app: validated application factory.
    - app: module-level instance served by the ASGI server.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.audit.schemas import AUDIT_SCHEMA_VERSION
from app.audit.sqlite import SqliteAuditRepository
from app.baseline.api.routes_health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security import security_middleware
from app.domain.support import DEFAULT_CASE_FIXTURE
from app.governance.composition import build_workflow_bundle
from app.governance.experiments import record_governed_experiment_manifest
from app.governance.llm import OpenAIGovernanceModel
from app.governance.persistence import SqliteGovernanceRepository, SqliteGovernanceUnitOfWork
from app.governance.security import GovernanceSecuritySettings, IdentityService
from app.governance.transport.http import router as governance_router
from app.governance.version import GOVERNED_APP_VERSION, WORKFLOW_SCHEMA_VERSION
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)


def create_governed_app(
    settings: Settings | None = None,
    governance_security: GovernanceSecuritySettings | None = None,
) -> FastAPI:
    """Create the Phase 4 governed HTTP application and composition boundary.

    Configuration and security policy are validated before the application is
    returned. Concrete retrieval, business-state, workflow, audit, and model
    adapters are created during the FastAPI lifespan so each application instance
    owns isolated runtime state.

    Args:
        settings: Optional validated shared settings. Environment settings are used
            when omitted.
        governance_security: Optional Phase 4 approval and audit-security settings.
            Environment-backed governance settings are used when omitted.

    Returns:
        A configured FastAPI application exposing health and governed-workflow
        routes.

    Raises:
        ValueError: If production or experiment governance security is incomplete.
    """
    base_settings = settings or get_settings()
    resolved_settings = base_settings.model_copy(
        update={
            "app_name": "Governed Agentic RAG",
            "app_version": GOVERNED_APP_VERSION,
        }
    )
    resolved_governance_security = governance_security or GovernanceSecuritySettings()
    resolved_governance_security.validate_runtime(
        production=resolved_settings.environment == "production",
        experiment=resolved_settings.execution_profile == "experiment",
    )
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        """Compose isolated adapters and attach the governed runtime to application state."""
        retriever = KnowledgeRetriever(resolved_settings)
        business_repository = SqliteSyntheticRepository(resolved_settings.synthetic_database_path)
        business_repository.initialize()
        if not business_repository.case_exists(DEFAULT_CASE_FIXTURE.case_id):
            business_repository.create_case(DEFAULT_CASE_FIXTURE)
        workflow_repository = SqliteGovernanceRepository(resolved_settings.synthetic_database_path)
        workflow_repository.initialize()
        audit_repository = SqliteAuditRepository(
            resolved_settings.synthetic_database_path,
            integrity_key=resolved_governance_security.resolve_audit_key(
                development_fallback=IdentityService(resolved_settings).derive_key(
                    "governance-audit-v1"
                )
            ),
        )
        audit_repository.initialize()

        application.state.retriever = retriever
        application.state.repository = business_repository
        application.state.governed_workflow = None
        application.state.agent = None
        application.state.experiment_manifest = None
        if resolved_settings.openai_api_key is not None:
            model = OpenAIGovernanceModel(resolved_settings)
            bundle = build_workflow_bundle(
                settings=resolved_settings,
                retriever=retriever,
                business_repository=business_repository,
                workflow_repository=workflow_repository,
                audit_repository=audit_repository,
                unit_of_work=SqliteGovernanceUnitOfWork(resolved_settings.synthetic_database_path),
                model=model,
            )
            application.state.governed_workflow = bundle.workflow
            application.state.agent = bundle.workflow

            if resolved_settings.execution_profile == "experiment":
                manifest, manifest_path = record_governed_experiment_manifest(
                    resolved_settings,
                    bundle.tool_router,
                )
                application.state.experiment_manifest = manifest
                logger.info(
                    "Governed experiment manifest recorded",
                    extra={
                        "context": {
                            "run_id": manifest.run_id,
                            "manifest_path": str(manifest_path),
                            "configuration_sha256": manifest.configuration_sha256,
                        }
                    },
                )
        logger.info(
            "Governed application initialized",
            extra={
                "context": {
                    "retrieval_backend": retriever.backend_name,
                    "model_configured": application.state.governed_workflow is not None,
                    "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
                    "audit_schema_version": AUDIT_SCHEMA_VERSION,
                }
            },
        )
        yield

    application = FastAPI(
        title="Governed Agentic RAG",
        version=resolved_settings.app_version,
        description=(
            "Phase 4 seven-stage governance-aware workflow treatment over the "
            "frozen Phase 3 shared substrate."
        ),
        lifespan=lifespan,
        docs_url=None if resolved_settings.environment == "production" else "/docs",
        redoc_url=None if resolved_settings.environment == "production" else "/redoc",
        openapi_url=None if resolved_settings.environment == "production" else "/openapi.json",
    )
    application.state.settings = resolved_settings
    application.state.governance_security = resolved_governance_security
    application.state.agent = None
    application.state.governed_workflow = None
    application.state.retriever = None
    application.state.repository = None
    application.state.experiment_manifest = None
    application.middleware("http")(security_middleware)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=resolved_settings.allowed_hosts,
    )
    application.include_router(health_router, prefix=resolved_settings.api_prefix)
    application.include_router(governance_router, prefix=resolved_settings.api_prefix)
    return application


app = create_governed_app()
