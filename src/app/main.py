from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes_baseline import router as baseline_router
from app.api.routes_health import router as health_router
from app.baseline.agent import BaselineAgent
from app.baseline.model import OpenAIResponsesModel
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security import security_middleware
from app.persistence.models import DEFAULT_CASE_FIXTURE
from app.persistence.repository import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.registry import build_shared_tools

logger = logging.getLogger(__name__)


# create_app function initializes the FastAPI application
def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        retriever = KnowledgeRetriever(resolved_settings)
        repository = SqliteSyntheticRepository(resolved_settings.synthetic_database_path)
        repository.initialize()
        if not repository.case_exists(DEFAULT_CASE_FIXTURE.case_id):
            repository.create_case(DEFAULT_CASE_FIXTURE)
        application.state.retriever = retriever
        application.state.repository = repository
        application.state.agent = None
        application.state.experiment_manifest = None
        if resolved_settings.openai_api_key is not None:
            model = OpenAIResponsesModel(resolved_settings)
            router = ToolRouter(
                build_shared_tools(retriever, repository),
                fault_injector=RepositoryFaultInjector(repository),
            )
            application.state.agent = BaselineAgent(
                settings=resolved_settings,
                retriever=retriever,
                model=model,
                tool_router=router,
                repository=repository,
            )
        logger.info(
            "Baseline application initialized",
            extra={
                "context": {
                    "retrieval_backend": retriever.backend_name,
                    "knowledge_chunks": retriever.chunk_count,
                    "model_configured": application.state.agent is not None,
                }
            },
        )
        yield

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Phase-3 conventional agentic RAG baseline.",
        lifespan=lifespan,
    )

    application.state.settings = resolved_settings
    application.state.agent = None
    application.state.retriever = None
    application.state.repository = None
    application.middleware("http")(security_middleware)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=resolved_settings.allowed_hosts,
    )
    application.include_router(health_router, prefix=resolved_settings.api_prefix)
    application.include_router(baseline_router, prefix=resolved_settings.api_prefix)
    return application


app = create_app()
