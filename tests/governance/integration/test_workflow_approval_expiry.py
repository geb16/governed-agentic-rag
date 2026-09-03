"""Integration coverage for durable approval-expiry behavior."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.audit.schemas import AuditEventType
from app.governance.contracts import (
    ApprovalCommand,
    ApprovalStatus,
    ApprovalValidationError,
    GovernedRequest,
    WorkflowConflictError,
    WorkflowStage,
    WorkflowStatus,
)
from app.governance.persistence import SqliteGovernanceRepository
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from tests.governance.integration.workflow_support import expire_approval_route, refund_model
from tests.governance.support import TEST_APPROVAL_PRINCIPAL, build_governed_workflow


def test_expired_approval_cannot_resume_execution(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Reject a correctly bound approval after its persisted deadline."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    assert pending.approval_route is not None
    with sqlite3.connect(settings.synthetic_database_path) as connection:
        connection.execute(
            "UPDATE governance_approvals SET expires_at = ? WHERE workflow_id = ?",
            (
                (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                pending.workflow_id,
            ),
        )

    with pytest.raises(ApprovalValidationError, match="expired"):
        workflow.approve(
            pending.workflow_id,
            ApprovalCommand(
                role="finance_manager",
                approved=True,
                proposal_digest=pending.approval_route.proposal_digest,
                expected_state_version=pending.state_version,
            ),
            TEST_APPROVAL_PRINCIPAL,
        )


def test_pending_approval_before_expiry_is_not_swept(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Leave a pending workflow unchanged when read before its deadline."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    assert pending.status == WorkflowStatus.PENDING_APPROVAL

    read_back = workflow.get_response(pending.workflow_id)

    assert read_back.status == WorkflowStatus.PENDING_APPROVAL
    assert [item.status for item in read_back.approvals] == [ApprovalStatus.PENDING]
    events = workflow.audit_trace(pending.workflow_id).events
    assert not any(event.event_type == AuditEventType.APPROVAL_EXPIRED for event in events)


def test_expiry_immediately_after_deadline_denies_on_read(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Sweep a workflow to denied when read immediately after its deadline."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    expire_approval_route(
        settings.synthetic_database_path,
        pending.workflow_id,
        when=datetime.now(UTC) - timedelta(microseconds=1),
    )

    response = workflow.get_response(pending.workflow_id)

    assert response.status == WorkflowStatus.DENIED
    assert response.error_code == "approval_expired"
    assert [item.status for item in response.approvals] == [ApprovalStatus.EXPIRED]
    events = workflow.audit_trace(pending.workflow_id).events
    expiry_events = [
        event for event in events if event.event_type == AuditEventType.APPROVAL_EXPIRED
    ]
    assert len(expiry_events) == 1


def test_repeated_reads_after_expiry_emit_one_audit_event(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Keep repeated reads idempotent after an approval expires."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    expire_approval_route(
        settings.synthetic_database_path,
        pending.workflow_id,
        when=datetime.now(UTC) - timedelta(seconds=1),
    )

    first = workflow.get_response(pending.workflow_id)
    second = workflow.get_response(pending.workflow_id)
    summary = workflow.get_summary(pending.workflow_id)

    assert first.status == WorkflowStatus.DENIED
    assert first.state_version == second.state_version
    assert second.status == WorkflowStatus.DENIED
    assert summary.status == WorkflowStatus.DENIED
    events = workflow.audit_trace(pending.workflow_id).events
    expiry_events = [
        event for event in events if event.event_type == AuditEventType.APPROVAL_EXPIRED
    ]
    assert len(expiry_events) == 1


def test_decision_after_expiry_is_rejected_deterministically(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Reject rather than apply a decision submitted after route expiry."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    assert pending.approval_route is not None
    expire_approval_route(
        settings.synthetic_database_path,
        pending.workflow_id,
        when=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(WorkflowConflictError):
        workflow.approve(
            pending.workflow_id,
            ApprovalCommand(
                role="finance_manager",
                approved=True,
                proposal_digest=pending.approval_route.proposal_digest,
                expected_state_version=pending.state_version,
                comment="Late approval attempt after the window elapsed.",
            ),
            TEST_APPROVAL_PRINCIPAL,
        )

    denied = workflow.get_response(pending.workflow_id)
    assert denied.status == WorkflowStatus.DENIED
    assert denied.error_code == "approval_expired"
    events = workflow.audit_trace(pending.workflow_id).events
    expiry_events = [
        event for event in events if event.event_type == AuditEventType.APPROVAL_EXPIRED
    ]
    assert len(expiry_events) == 1


def test_workflow_reaches_finalized_terminal_state_after_expiry(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Fully finalize a swept workflow instead of only marking it denied."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    expire_approval_route(
        settings.synthetic_database_path,
        pending.workflow_id,
        when=datetime.now(UTC) - timedelta(seconds=1),
    )

    response = workflow.get_response(pending.workflow_id)

    assert response.status == WorkflowStatus.DENIED
    assert response.current_stage == WorkflowStage.FINAL_RESPONSE_AUDIT
    assert response.answer is not None
    assert response.tool_calls == []
    trace = workflow.audit_trace(pending.workflow_id)
    assert trace.chain_valid is True
    assert any(event.event_type == AuditEventType.WORKFLOW_COMPLETED for event in trace.events)


def test_expired_denial_persists_and_reloads_from_a_fresh_repository(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Reload a swept, finalized denial from the durable store."""
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(75_000),
    )
    pending = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 750 refund on ticket TKT-1003 with all details",
        )
    )
    expire_approval_route(
        settings.synthetic_database_path,
        pending.workflow_id,
        when=datetime.now(UTC) - timedelta(seconds=1),
    )
    workflow.get_response(pending.workflow_id)

    reloaded_repository = SqliteGovernanceRepository(settings.synthetic_database_path)
    reloaded = reloaded_repository.get(pending.workflow_id)

    assert reloaded is not None
    assert reloaded.status == WorkflowStatus.DENIED
    assert reloaded.error_code == "approval_expired"
    assert reloaded.current_stage == WorkflowStage.FINAL_RESPONSE_AUDIT
    assert reloaded.final is not None
    assert [item.status for item in reloaded.approvals] == [ApprovalStatus.EXPIRED]
