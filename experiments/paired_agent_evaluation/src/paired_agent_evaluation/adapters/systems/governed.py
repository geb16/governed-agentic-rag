"""Runs the frozen governed workflow and captures evaluation observations.

Each execution receives isolated business, workflow, and audit state. Pending
approvals are replayed from the case's expected human decisions, after which the
runner records evidence, state changes, audit integrity, latency, and failures.
"""

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

from paired_agent_evaluation.application.ports import AcceptanceRecorder
from paired_agent_evaluation.domain.executions import ScheduledExecution
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)

from ._shared import RecordingRetriever, state_snapshot
from .acceptance import AcceptanceAwareGovernanceModel

ROLE_ALIASES = {
    "iam_manager": "iam_administrator",
    "support_supervisor": "support_manager",
}


def _canonical_role(role: str) -> str:
    """Maps legacy dataset roles to their governed-workflow equivalents."""
    return ROLE_ALIASES.get(role, role)


class GovernedSystemRunner:
    """Executes evaluation cases against the governed workflow.

    Args:
        settings: Runtime configuration copied for each isolated execution.
        retriever_factory: Factory for the retrieval backend.
        model_factory: Factory for the governed model gateway.
    """

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
        *,
        acceptance: AcceptanceRecorder,
    ) -> RawExecution:
        """Runs one scheduled case and captures its complete observation.

        The runner initializes isolated repositories, invokes the workflow, and
        deterministically replays matching approval decisions from the dataset.
        It captures the initial and final responses, cited evidence, audit trace,
        acceptance status, latency, and business-state changes. Runtime failures
        become error-bearing observations with any evidence already collected.

        Args:
            case: Evaluation case, including fixture and expected decisions.
            scheduled: Schedule entry that identifies condition and repetition.
            workspace: Isolated directory for execution artifacts.
            acceptance: Recorder controlling whether retry remains safe.

        Returns:
            The successful or failed raw execution observation.
        """
        workspace.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)
        started = perf_counter()
        database_path = workspace / "synthetic.db"
        before = BusinessState()
        retriever: RecordingRetriever | None = None
        try:
            settings = self._settings.model_copy(update={"synthetic_database_path": database_path})
            business = SqliteSyntheticRepository(database_path)
            business.initialize()
            business.create_case(case.fixture)
            before = state_snapshot(database_path, case.case_id)
            workflows = SqliteGovernanceRepository(database_path)
            workflows.initialize()
            audit = SqliteAuditRepository(
                database_path,
                integrity_key=IdentityService(settings).derive_key("governance-audit-v1"),
            )
            audit.initialize()
            retriever = RecordingRetriever(self._retriever_factory(settings))
            model = AcceptanceAwareGovernanceModel(
                self._model_factory(settings),
                acceptance,
            )
            bundle = build_workflow_bundle(
                settings=settings,
                retriever=retriever,
                business_repository=business,
                workflow_repository=workflows,
                audit_repository=audit,
                unit_of_work=SqliteGovernanceUnitOfWork(database_path),
                model=model,
            )
            initial = bundle.workflow.invoke(
                GovernedRequest.model_validate(case.request.model_dump())
            )
            response = initial
            decisions = {
                _canonical_role(item.role): item.decision.value
                for item in case.expected.human_decisions
            }
            if initial.status == WorkflowStatus.PENDING_APPROVAL:
                for approval in list(initial.approvals):
                    decision = decisions.get(_canonical_role(approval.role))
                    if decision is None:
                        continue
                    response = bundle.workflow.approve(
                        initial.workflow_id,
                        ApprovalCommand(
                            role=approval.role,
                            approved=decision == "approve",
                            proposal_digest=approval.proposal_digest,
                            expected_state_version=response.state_version,
                            comment="Deterministic Phase 5 decision replay.",
                        ),
                        ApprovalPrincipal(
                            subject_id=f"evaluation-reviewer-{approval.role}",
                            roles=frozenset({approval.role}),
                        ),
                    )
                    if response.status != WorkflowStatus.PENDING_APPROVAL:
                        break
            state = workflows.get(response.workflow_id)
            response_payload = response.model_dump(mode="json")
            response_payload["_evaluation_cited_evidence_ids"] = (
                list(state.final.cited_evidence_ids) if state is not None and state.final else []
            )
            trace = bundle.workflow.audit_trace(response.workflow_id)

            if response.status != WorkflowStatus.FAILED:
                acceptance.mark_accepted()
            pre_acceptance_error = model.last_error if not acceptance.accepted else None

            first_event = next(
                (event for event in trace.events if event.event_type.value == "workflow_started"),
                None,
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
                initial_response=initial.model_dump(mode="json"),
                response=response_payload,
                retrieved=retriever.evidence(),
                retrieval_call_count=len(retriever.calls),
                state_before=before,
                state_after=state_snapshot(database_path, case.case_id),
                audit_events=[event.model_dump(mode="json") for event in trace.events],
                audit_chain_valid=trace.chain_valid,
                audit_workflow_id=trace.workflow_id,
                audit_trace_id=first_event.trace_id if first_event else None,
                audit_request_id=(
                    str(first_event.details["request_id"])
                    if first_event and "request_id" in first_event.details
                    else None
                ),
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
