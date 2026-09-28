"""Create the FastAPI application and the process-level app instance.

create_app builds the Phase 3 HTTP service from validated settings: JSON
logging, host allowlisting (outermost middleware), request-size checks with
security headers, and health and baseline routers under the API prefix.
Concrete adapters are composed by build_runtime inside the lifespan and
attached to app.state, so each instance owns its resources and tests can
inject isolated settings. Interactive docs and OpenAPI are off in production.
Core:
    - create_app: application factory with lifespan-scoped runtime wiring.
    - app: module-level instance served by the ASGI server.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.baseline.api.routes_baseline import router as baseline_router
from app.baseline.api.routes_health import router as health_router
from app.baseline.composition import build_runtime
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security import security_middleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the Phase 3 HTTP application without global runtime adapters.

    Concrete adapters are created during the FastAPI lifespan so each application
    instance owns its resources and tests can provide isolated settings.

    Args:
        settings: Optional validated settings override. Environment settings are used
            when omitted.

    Returns:
        A configured FastAPI application with health and baseline routers.
    """
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        """Attach one composed runtime for the duration of the application lifespan."""
        runtime = build_runtime(resolved_settings)
        application.state.retriever = runtime.retriever
        application.state.repository = runtime.repository
        application.state.agent = runtime.agent
        application.state.experiment_manifest = runtime.experiment_manifest
        logger.info(
            "Baseline application initialized",
            extra={
                "context": {
                    "retrieval_backend": runtime.retriever.backend_name,
                    "knowledge_chunks": runtime.retriever.chunk_count,
                    "model_configured": runtime.agent is not None,
                    "experiment_manifest_recorded": runtime.experiment_manifest is not None,
                }
            },
        )
        yield

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Phase-3 conventional agentic RAG baseline.",
        lifespan=lifespan,
        docs_url=None if resolved_settings.environment == "production" else "/docs",
        redoc_url=None if resolved_settings.environment == "production" else "/redoc",
        openapi_url=None if resolved_settings.environment == "production" else "/openapi.json",
    )

    application.state.settings = resolved_settings
    application.state.agent = None
    application.state.retriever = None
    application.state.repository = None
    application.state.experiment_manifest = None
    application.middleware("http")(security_middleware)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=resolved_settings.allowed_hosts,
    )
    application.include_router(health_router, prefix=resolved_settings.api_prefix)
    application.include_router(baseline_router, prefix=resolved_settings.api_prefix)
    return application


app = create_app()
