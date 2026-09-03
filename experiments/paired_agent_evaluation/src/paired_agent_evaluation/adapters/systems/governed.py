"""Adapter that invokes and deterministically resumes the frozen governed workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.audit.sqlite import SqliteAuditRepository
from app.core.config import Settings
from app.evaluation.dataset.models import EvaluationCase
from app.governance.composition import build_workflow_bundle
from app.governance.contracts import ApprovalCommand, ApprovalPrincipal, GovernedRequest
from app.governance.contracts.enums import WorkflowStatus
from app.governance.llm import GovernanceModel, OpenAIGovernanceModel
from app.governance.persistence import SqliteGovernanceRepository, SqliteGovernanceUnitOfWork
from app.governance.security import IdentityService
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever, Retriever

from paired_agent_evaluation.adapters.systems._shared import RecordingRetriever, state_snapshot
from paired_agent_evaluation.domain.executions import ScheduledExecution
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)

ROLE_ALIASES = {
    "iam_manager": "iam_administrator",
    "support_supervisor": "support_manager",
}


def _canonical_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)


class GovernedSystemRunner:
    def __init__(
        self,
        settings: Settings,
        *,
        retriever_factory: Callable[[Settings], Retriever] = KnowledgeRetriever,
        model_factory: Callable[[Settings], GovernanceModel] = OpenAIGovernanceModel,
    ) -> None:
        self._settings = settings
        self._retriever_factory = retriever_factory
        self._model_factory = model_factory

    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
    ) -> RawExecution:
        pass