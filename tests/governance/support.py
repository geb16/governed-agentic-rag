"""Deterministic Phase 4 model double and isolated workflow builder."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from app.audit.ports import AuditRepository
from app.audit.schemas import (
    AuditActorType,
    AuditEvent,
    AuditEventType,
    AuditStage,
    AuditTrace,
)
from app.audit.sqlite import SqliteAuditRepository
from app.core.config import Settings
from app.governance.composition import build_workflow_bundle
from app.governance.contracts import (
    ApprovalPrincipal,
    ClassificationDraft,
    GovernedFinalDraft,
    GovernedRequest,
    ProposedActionDraft,
    RetrievalResult,
    Sensitivity,
    TaskIntent,
    TaskType,
    ToolDefinition,
    WorkflowState,
)
from app.governance.llm import GovernanceModel, ModelResult
from app.governance.orchestration import GovernedWorkflow
from app.governance.persistence import SqliteGovernanceRepository, SqliteGovernanceUnitOfWork
from app.governance.security import IdentityService
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever

TEST_APPROVAL_PRINCIPAL = ApprovalPrincipal(
    subject_id="governance-reviewer",
    roles=frozenset({"finance_manager", "fraud_reviewer", "iam_administrator"}),
)


class InjectedAuditFailure(RuntimeError):
    """Deterministic failure used to verify transaction rollback behavior."""


class InjectedModelFailure(RuntimeError):
    """Deterministic model failure used to verify fail-closed attribution."""


class FailingAuditRepository:
    """Delegate audit operations except for one selected event type."""

    def __init__(self, delegate: AuditRepository, fail_on: AuditEventType) -> None:
        self._delegate = delegate
        self._fail_on = fail_on

    def initialize(self) -> None:
        self._delegate.initialize()

    def append(
        self,
        *,
        workflow_id: str,
        trace_id: str,
        stage: AuditStage,
        event_type: AuditEventType,
        actor_type: AuditActorType,
        actor_id: str | None = None,
        input_value: Any | None = None,
        output_value: Any | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        if event_type == self._fail_on:
            raise InjectedAuditFailure(event_type.value)
        return self._delegate.append(
            workflow_id=workflow_id,
            trace_id=trace_id,
            stage=stage,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            input_value=input_value,
            output_value=output_value,
            details=details,
        )

    def list_events(self, workflow_id: str) -> list[AuditEvent]:
        return self._delegate.list_events(workflow_id)

    def trace(self, workflow_id: str) -> AuditTrace:
        return self._delegate.trace(workflow_id)


def audit_integrity_key(settings: Settings) -> bytes:
    """Return the same purpose-bound audit key used by the governed application."""

    return IdentityService(settings).derive_key("governance-audit-v1")


def material_refund_model() -> ScriptedGovernanceModel:
    """Return a deterministic proposal that requires finance-manager approval."""

    return ScriptedGovernanceModel(
        classifications=[
            ClassificationDraft(
                intent=TaskIntent.REFUND,
                task_type=TaskType.STATE_CHANGING,
                sensitivity=Sensitivity.MODERATE,
                confidence=0.95,
                summary="A material refund was requested.",
            )
        ],
        proposals=[
            ProposedActionDraft(
                kind="tool",  # type: ignore[arg-type]
                tool_name="issue_refund",
                arguments_json=json.dumps(
                    {
                        "ticket_id": "TKT-1003",
                        "amount_minor": 75_000,
                        "currency": "GBP",
                        "idempotency_key": "api-refund-001",
                    }
                ),
                confidence=0.95,
                rationale="The evidence supports a candidate refund.",
            )
        ],
        finals=[GovernedFinalDraft(answer="Completed.", grounded=False)],
    )


class ScriptedGovernanceModel(GovernanceModel):
    def __init__(
        self,
        *,
        classifications: list[ClassificationDraft] | None = None,
        proposals: list[ProposedActionDraft] | None = None,
        finals: list[GovernedFinalDraft] | None = None,
        fail_on: str | None = None,
    ) -> None:
        self._fail_on = fail_on
        self._classifications: Iterator[ClassificationDraft] = iter(
            classifications
            or [
                ClassificationDraft(
                    intent=TaskIntent.INFORMATION,
                    task_type=TaskType.READ_ONLY,
                    sensitivity=Sensitivity.LOW,
                    confidence=0.95,
                    summary="Read-only support request.",
                )
            ]
        )
        self._proposals: Iterator[ProposedActionDraft] = iter(
            proposals
            or [
                ProposedActionDraft(
                    kind="respond",  # type: ignore
                    response_text="A grounded response is available.",
                    confidence=0.95,
                    rationale="No tool action is needed.",
                )
            ]
        )
        self._finals: Iterator[GovernedFinalDraft] = iter(
            finals
            or [
                GovernedFinalDraft(
                    answer="The workflow completed safely.",
                    grounded=False,
                )
            ]
        )
        self.calls: list[tuple[str, Any]] = []

    @property
    def model_name(self) -> str:
        return "scripted-governance-model"

    def classify(
        self,
        request: GovernedRequest,
        *,
        safety_identifier: str,
    ) -> ModelResult[ClassificationDraft]:
        if self._fail_on == "classify":
            raise InjectedModelFailure("classify")
        self.calls.append(("classify", request.request_id))
        return ModelResult(next(self._classifications), input_tokens=10, output_tokens=3)

    def propose(
        self,
        request: GovernedRequest,
        classification: ClassificationDraft,
        retrieval: RetrievalResult,
        tools: list[ToolDefinition],
        *,
        safety_identifier: str,
    ) -> ModelResult[ProposedActionDraft]:
        if self._fail_on == "propose":
            raise InjectedModelFailure("propose")
        self.calls.append(("propose", [item.name for item in tools]))
        return ModelResult(next(self._proposals), input_tokens=20, output_tokens=5)

    def finalize(
        self,
        state: WorkflowState,
        *,
        safety_identifier: str,
    ) -> ModelResult[GovernedFinalDraft]:
        if self._fail_on == "finalize":
            raise InjectedModelFailure("finalize")
        self.calls.append(("finalize", state.status.value))
        return ModelResult(next(self._finals), input_tokens=15, output_tokens=4)


def build_governed_workflow(
    *,
    settings: Settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
    model: ScriptedGovernanceModel,
    audit_repository: AuditRepository | None = None,
) -> GovernedWorkflow:
    """
    Build the governed workflow with the provided retriever, repository, model, and audit store.
    """
    workflow_repository = SqliteGovernanceRepository(settings.synthetic_database_path)
    workflow_repository.initialize()
    resolved_audit_repository = audit_repository or SqliteAuditRepository(
        settings.synthetic_database_path,
        integrity_key=audit_integrity_key(settings),
    )
    resolved_audit_repository.initialize()
    return build_workflow_bundle(
        settings=settings,
        retriever=retriever,
        business_repository=repository,
        workflow_repository=workflow_repository,
        audit_repository=resolved_audit_repository,
        unit_of_work=SqliteGovernanceUnitOfWork(settings.synthetic_database_path),
        model=model,
    ).workflow
