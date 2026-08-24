"""Declare the injected ports and stage services required by orchestration.

``WorkflowRuntime`` is an explicit dependency container, not a service locator. It
keeps the use case testable and prevents orchestration from constructing concrete
provider, retrieval, persistence, audit, or tool adapters.
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from app.audit.ports import AuditRepository
from app.core.config import Settings
from app.domain.repositories import SyntheticRepository
from app.governance.persistence import WorkflowRepository
from app.governance.stages import (
    ApprovalRoutingStage,
    FinalResponseStage,
    KnowledgeRetrievalStage,
    ProposedActionStage,
    RetryRecoveryStage,
    TaskClassificationStage,
)
from app.governance.stages.risk import RiskCheckingStage
from app.rag.retriever import Retriever


class GovernanceUnitOfWork(Protocol):
    """Atomic boundary for workflow state and required audit writes."""

    def transaction(self) -> AbstractContextManager[None]:
        """Return a context that commits or rolls back state and audit together."""
        ...


@dataclass(frozen=True, slots=True)
class WorkflowRuntime:
    """Group immutable ports and bounded stages for one workflow instance.

    Attributes:
        settings: Shared validated runtime limits and profile.
        retriever: Shared retrieval port used for backend identity and stage two.
        business_repository: Shared synthetic case repository.
        workflows: Durable governed-state and approval port.
        audit: Keyed append-only audit repository port.
        unit_of_work: Atomic state-and-audit transaction boundary.
        classification: Stage-one classification service.
        retrieval: Stage-two knowledge service.
        proposal: Stage-three proposal and validation service.
        risk: Stage-four deterministic policy service.
        approval: Stage-five deterministic routing service.
        recovery: Stage-six bounded execution service.
        final: Stage-seven output-validation service.
        model_name: Provider model identity exposed for traceability.
    """

    settings: Settings
    retriever: Retriever
    business_repository: SyntheticRepository
    workflows: WorkflowRepository
    audit: AuditRepository
    unit_of_work: GovernanceUnitOfWork
    classification: TaskClassificationStage
    retrieval: KnowledgeRetrievalStage
    proposal: ProposedActionStage
    risk: RiskCheckingStage
    approval: ApprovalRoutingStage
    recovery: RetryRecoveryStage
    final: FinalResponseStage
    model_name: str
