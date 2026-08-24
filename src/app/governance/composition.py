"""Compose the governed use case from explicit ports and shared capabilities.

This module is the Phase 4 composition boundary below the FastAPI entry point. It
wires concrete dependencies supplied by the application, constructs deterministic
stages, and returns both the workflow and the exact router included in experiment
identity. No request-specific state is retained here.
"""

from dataclasses import dataclass

from app.audit.ports import AuditRepository
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.repositories import SyntheticRepository
from app.governance.llm import GovernanceModel
from app.governance.orchestration import GovernedWorkflow, WorkflowRuntime
from app.governance.orchestration.dependencies import GovernanceUnitOfWork
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
from app.governance.tools import ToolCatalog
from app.rag.retriever import Retriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.registry import build_shared_tools


@dataclass(frozen=True, slots=True)
class WorkflowBundle:
    """Return the governed use case and its experiment-identified tool router.

    Attributes:
        workflow: Fully composed public seven-stage use case.
        tool_router: Shared simulated router whose schemas enter the run manifest.
    """

    workflow: GovernedWorkflow
    tool_router: ToolRouter


def build_workflow_bundle(
    *,
    settings: Settings,
    retriever: Retriever,
    business_repository: SyntheticRepository,
    workflow_repository: WorkflowRepository,
    audit_repository: AuditRepository,
    unit_of_work: GovernanceUnitOfWork,
    model: GovernanceModel,
) -> WorkflowBundle:
    """Compose the governed application from explicit ports and shared adapters.

    Args:
        settings: Validated runtime profile, provider limits, and security settings.
        retriever: Shared lexical or Qdrant retrieval port.
        business_repository: Shared synthetic business-state repository.
        workflow_repository: Durable governed-state and approval port.
        audit_repository: Keyed append-only audit repository port.
        unit_of_work: Atomic boundary joining workflow and audit writes.
        model: Provider-neutral structured governance model port.

    Returns:
        Fully composed workflow and the router used for bounded execution and
        experiment tool-schema identity.

    Note:
        The same retriever, business repository, and simulated tool implementations
        are shared with the baseline condition to preserve experimental comparability.
    """
    tools = build_shared_tools(retriever, business_repository)
    tool_router = ToolRouter(
        tools,
        fault_injector=RepositoryFaultInjector(business_repository),
    )
    runtime = WorkflowRuntime(
        settings=settings,
        retriever=retriever,
        business_repository=business_repository,
        workflows=workflow_repository,
        audit=audit_repository,
        unit_of_work=unit_of_work,
        classification=TaskClassificationStage(model),
        retrieval=KnowledgeRetrievalStage(retriever),
        proposal=ProposedActionStage(model, ToolCatalog(tools)),
        risk=RiskCheckingStage(),
        approval=ApprovalRoutingStage(),
        recovery=RetryRecoveryStage(tool_router),
        final=FinalResponseStage(model),
        model_name=model.model_name,
    )
    return WorkflowBundle(
        workflow=GovernedWorkflow(runtime),
        tool_router=tool_router,
    )
