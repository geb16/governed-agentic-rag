"""Assemble concrete adapters and services for one application lifespan.

Composition root: builds the retriever, initializes and seeds the SQLite
synthetic repository, and, only when an OpenAI key is set, wires the model,
tool router, fault injector, and BaselineAgent. Experiment profiles also
record an immutable run manifest. Side effects: database and manifest writes.
Core:
    - ApplicationRuntime: frozen bundle of lifespan adapters.
    - build_runtime: wires and returns the ApplicationRuntime.
References:
    [1] M. Seemann, "Composition Root." https://blog.ploeh.dk/2011/07/28/CompositionRoot/
"""

from __future__ import annotations

from dataclasses import dataclass

from app.baseline.agent import BaselineAgent
from app.baseline.experiments import ExperimentRunManifest, record_experiment_manifest
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.support import DEFAULT_CASE_FIXTURE
from app.infrastructure.llm.openai_responses import OpenAIResponsesModel
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.registry import build_shared_tools


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    """Adapters assembled for one application lifespan."""

    retriever: KnowledgeRetriever
    repository: SqliteSyntheticRepository
    agent: BaselineAgent | None
    experiment_manifest: ExperimentRunManifest | None


def build_runtime(settings: Settings) -> ApplicationRuntime:
    """Assemble adapters and initialize isolated synthetic state.

    Args:
        settings: Validated process configuration.

    Returns:
        A runtime containing retrieval, persistence, an optional model-backed agent,
        and the automatically recorded identity for an experiment-profile run.
    """

    retriever = KnowledgeRetriever(settings)
    repository = SqliteSyntheticRepository(settings.synthetic_database_path)
    repository.initialize()
    if not repository.case_exists(DEFAULT_CASE_FIXTURE.case_id):
        repository.create_case(DEFAULT_CASE_FIXTURE)

    agent: BaselineAgent | None = None
    experiment_manifest: ExperimentRunManifest | None = None
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
        if settings.execution_profile == "experiment":
            experiment_manifest, _ = record_experiment_manifest(settings, tool_router)

    return ApplicationRuntime(
        retriever=retriever,
        repository=repository,
        agent=agent,
        experiment_manifest=experiment_manifest,
    )
