"""Failure-atomicity and fail-closed integration tests for governed orchestration."""

from __future__ import annotations

import json
import sqlite3

import pytest

from app.audit.schemas import AuditEventType, AuditStage
from app.audit.sqlite import SqliteAuditRepository
from app.governance.contracts import (
    ApprovalCommand,
    ApprovalPrincipal,
    ClassificationDraft,
    GovernedFinalDraft,
    GovernedRequest,
    ProposedActionDraft,
    ProposedActionKind,
    Sensitivity,
    TaskIntent,
    TaskType,
    WorkflowConflictError,
    WorkflowStatus,
)
from app.governance.orchestration.errors import ApprovalAuthorizationError
from app.governance.persistence import SqliteGovernanceRepository
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from tests.governance.support import (
    FailingAuditRepository,
    InjectedAuditFailure,
    ScriptedGovernanceModel,
    audit_integrity_key,
    build_governed_workflow,
)


def _refund_model() -> ScriptedGovernanceModel:
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
                kind=ProposedActionKind.TOOL,
                tool_name="issue_refund",
                arguments_json=json.dumps(
                    {
                        "ticket_id": "TKT-1003",
                        "amount_minor": 75_000,
                        "currency": "GBP",
                        "idempotency_key": "atomic-refund-001",
                    }
                ),
                confidence=0.95,
                rationale="The evidence supports a candidate refund.",
            )
        ],
        finals=[GovernedFinalDraft(answer="Completed.", grounded=False)],
    )


def test_workflow_creation_rolls_back_when_required_audit_fails(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Allow the same request to retry after the initial audit write fails."""

    base_audit = SqliteAuditRepository(
        settings.synthetic_database_path,
        integrity_key=audit_integrity_key(settings),
    )
    failing = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=ScriptedGovernanceModel(),
        audit_repository=FailingAuditRepository(base_audit, AuditEventType.WORKFLOW_STARTED),
    )
    request = GovernedRequest(
        request_id="req_atomic_creation",
        requester_id="support-user",
        query="Explain the normal support escalation policy",
    )

    with pytest.raises(InjectedAuditFailure):
        failing.invoke(request)

    healthy = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=ScriptedGovernanceModel(),
    )
    assert healthy.invoke(request).status == WorkflowStatus.COMPLETED


@pytest.mark.parametrize(
    "failed_event",
    [AuditEventType.APPROVAL_RECORDED, AuditEventType.WORKFLOW_RESUMED],
)
def test_approval_decision_rolls_back_when_required_audit_fails(
    failed_event: AuditEventType,
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Keep the approval pending when its mandatory audit record cannot commit."""

    base_audit = SqliteAuditRepository(
        settings.synthetic_database_path,
        integrity_key=audit_integrity_key(settings),
    )
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=_refund_model(),
        audit_repository=FailingAuditRepository(base_audit, failed_event),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    assert pending.approval_route is not None
    command = ApprovalCommand(
        role="finance_manager",
        approved=True,
        proposal_digest=pending.approval_route.proposal_digest,
        expected_state_version=pending.state_version,
    )
    principal = ApprovalPrincipal(
        subject_id="finance-reviewer",
        roles=frozenset({"finance_manager"}),
    )

    with pytest.raises(InjectedAuditFailure):
        workflow.approve(pending.workflow_id, command, principal)

    unchanged = workflow.get_response(pending.workflow_id)
    assert unchanged.status == WorkflowStatus.PENDING_APPROVAL
    assert unchanged.state_version == pending.state_version
    assert unchanged.approvals[0].status.value == "pending"


def test_approval_rejects_a_principal_without_the_required_role(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Keep a pending decision unchanged when trusted role bindings do not authorize it."""

    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=_refund_model(),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    assert pending.approval_route is not None

    with pytest.raises(ApprovalAuthorizationError):
        workflow.approve(
            pending.workflow_id,
            ApprovalCommand(
                role="finance_manager",
                approved=True,
                proposal_digest=pending.approval_route.proposal_digest,
                expected_state_version=pending.state_version,
            ),
            ApprovalPrincipal(
                subject_id="support-reviewer",
                roles=frozenset({"support_supervisor"}),
            ),
        )

    assert workflow.get_response(pending.workflow_id).state_version == pending.state_version


def test_failure_event_identifies_the_stage_that_raised(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Do not attribute proposal-model failures to the preceding retrieval stage."""

    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=ScriptedGovernanceModel(fail_on="propose"),
    )

    response = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Explain the normal support escalation policy",
        )
    )
    failures = [
        event
        for event in workflow.audit_trace(response.workflow_id).events
        if event.event_type == AuditEventType.STAGE_FAILED
    ]

    assert response.status == WorkflowStatus.FAILED
    assert len(failures) == 1
    assert failures[0].stage == AuditStage.PROPOSED_ACTION_GENERATION


def test_repository_rejects_terminal_state_reopening_and_unknown_schema(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Protect state-machine and migration invariants below the orchestration layer."""

    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=ScriptedGovernanceModel(),
    )
    response = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Explain the normal support escalation policy",
        )
    )
    store = SqliteGovernanceRepository(settings.synthetic_database_path)
    completed = store.get(response.workflow_id)
    assert completed is not None

    with pytest.raises(WorkflowConflictError, match="completed -> running"):
        store.update(
            completed.model_copy(update={"status": WorkflowStatus.RUNNING}),
            expected_version=completed.state_version,
        )

    with sqlite3.connect(settings.synthetic_database_path) as connection:
        connection.execute(
            "UPDATE schema_metadata SET value = '999' WHERE key = 'governance_schema_version'"
        )
    with pytest.raises(RuntimeError, match="Unsupported governance schema version"):
        store.initialize()
