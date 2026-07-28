from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes_baseline import router as baseline_router
from app.api.routes_health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


# create_app function initializes the FastAPI application
def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
    )
    application.state.settings = resolved_settings
    application.state.agent = None
    application.state.retriever = None
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=resolved_settings.allowed_hosts,
    )
    application.include_router(health_router)
    application.include_router(baseline_router)
    return application


app = create_app()
