from __future__ import annotations

from dataclasses import dataclass

from app.baseline.agent import BaselineAgent
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.support import DEFAULT_CASE_FIXTURE
from app.infrastructure.llm.openai_responses import OpenAIResponsesModel
from app.persistence.repository import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.registry import build_shared_tools


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    """Adapters assembled for one application lifespan."""

    retriever: KnowledgeRetriever
    repository: SqliteSyntheticRepository
    agent: BaselineAgent | None


def build_runtime(settings: Settings) -> ApplicationRuntime:
    """Composition root: instantiate concrete adapters at the process boundary."""

    retriever = KnowledgeRetriever(settings)
    repository = SqliteSyntheticRepository(settings.synthetic_database_path)
    repository.initialize()
    if not repository.case_exists(DEFAULT_CASE_FIXTURE.case_id):
        repository.create_case(DEFAULT_CASE_FIXTURE)

    agent: BaselineAgent | None = None
    if settings.openai_api_key is not None:
        model = OpenAIResponsesModel(settings)
        tool_router = ToolRouter(
            build_shared_tools(retriever, repository),
            fault_injector=RepositoryFaultInjector(repository),
        )
        agent = BaselineAgent(
            settings=settings,
            retriever=retriever,
            model=model,
            tool_router=tool_router,
            repository=repository,
        )

    return ApplicationRuntime(
        retriever=retriever,
        repository=repository,
        agent=agent,
    )
