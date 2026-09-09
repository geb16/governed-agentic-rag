"""Adapter that invokes the frozen conventional baseline without changing it."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.baseline.agent import BaselineAgent
from app.baseline.application.contracts import AgentStatus, BaselineRequest
from app.baseline.application.ports import ModelGateway
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.evaluation.dataset.models import EvaluationCase
from app.infrastructure.llm.openai_responses import OpenAIResponsesModel
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever, Retriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.registry import build_shared_tools

from paired_agent_evaluation.adapters.systems._shared import RecordingRetriever, state_snapshot
from paired_agent_evaluation.adapters.systems.acceptance import AcceptanceAwareBaselineModel
from paired_agent_evaluation.application.ports import AcceptanceRecorder
from paired_agent_evaluation.domain.executions import ScheduledExecution
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)


class BaselineSystemRunner:
    def __init__(
        self,
        settings: Settings,
        *,
        retriever_factory: Callable[[Settings], Retriever] = KnowledgeRetriever,
        model_factory: Callable[[Settings], ModelGateway] = OpenAIResponsesModel,
    ) -> None:
        self._settings = settings
        self._retriever_factory = retriever_factory
        self._model_factory = model_factory

    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
        *,
        acceptance: AcceptanceRecorder,
    ) -> RawExecution:
        workspace.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)
        started = perf_counter()
        database_path = workspace / "synthetic.db"
        before = BusinessState()
        retriever: RecordingRetriever | None = None
        try:
            settings = self._settings.model_copy(update={"synthetic_database_path": database_path})
            repository = SqliteSyntheticRepository(database_path)
            repository.initialize()
            repository.create_case(case.fixture)
            before = state_snapshot(database_path, case.case_id)
            retriever = RecordingRetriever(self._retriever_factory(settings))
            model = AcceptanceAwareBaselineModel(self._model_factory(settings), acceptance)
            router = ToolRouter(
                build_shared_tools(retriever, repository),
                fault_injector=RepositoryFaultInjector(repository),
            )
            agent = BaselineAgent(
                settings=settings,
                retriever=retriever,
                model=model,
                tool_router=router,
                repository=repository,
            )
            response = agent.invoke(BaselineRequest.model_validate(case.request.model_dump()))
            if response.status != AgentStatus.FAILED:
                acceptance.mark_accepted()
            pre_acceptance_error = model.last_error if not acceptance.accepted else None
            return RawExecution(
                key=scheduled.key,
                acceptance=(
                    AcceptanceStatus.ACCEPTED if acceptance.accepted else AcceptanceStatus.INVALID
                ),
                request_accepted=acceptance.accepted,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                latency_ms=(perf_counter() - started) * 1000,
                request=case.request.model_dump(mode="json"),
                response=response.model_dump(mode="json"),
                retrieved=retriever.evidence(),
                retrieval_call_count=len(retriever.calls),
                state_before=before,
                state_after=state_snapshot(database_path, case.case_id),
                error_type=(
                    type(pre_acceptance_error).__name__
                    if pre_acceptance_error is not None
                    else None
                ),
                error_message=(
                    str(pre_acceptance_error)[:1000] if pre_acceptance_error is not None else None
                ),
            )
        except Exception as error:
            after = (
                state_snapshot(database_path, case.case_id) if database_path.exists() else before
            )
            return RawExecution(
                key=scheduled.key,
                acceptance=(
                    AcceptanceStatus.ACCEPTED if acceptance.accepted else AcceptanceStatus.INVALID
                ),
                request_accepted=acceptance.accepted,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                latency_ms=(perf_counter() - started) * 1000,
                request=case.request.model_dump(mode="json"),
                retrieved=retriever.evidence() if retriever is not None else [],
                retrieval_call_count=len(retriever.calls) if retriever is not None else 0,
                state_before=before,
                state_after=after,
                error_type=type(error).__name__,
                error_message=str(error)[:1000],
            )
