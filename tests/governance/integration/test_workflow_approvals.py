"""Integration coverage for approval-bound governed workflows."""

from __future__ import annotations

import pytest

from app.governance.contracts import (
    ApprovalCommand,
    ApprovalValidationError,
    GovernedRequest,
    WorkflowConflictError,
    WorkflowStatus,
)
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from tests.governance.integration.workflow_support import refund_model
from tests.governance.support import TEST_APPROVAL_PRINCIPAL, build_governed_workflow


def test_high_risk_action_pauses_and_resumes_after_bound_approval(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
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
    assert pending.answer is None
    assert [item.role for item in pending.approvals] == ["finance_manager"]
    assert pending.approval_route is not None
    assert repository.get_ticket("case_default", "TKT-1003") is not None

    completed = workflow.approve(
        pending.workflow_id,
        ApprovalCommand(
            role="finance_manager",
            approved=True,
            proposal_digest=pending.approval_route.proposal_digest,
            expected_state_version=pending.state_version,
            comment="Synthetic policy threshold checked.",
        ),
        TEST_APPROVAL_PRINCIPAL,
    )

    assert completed.status == WorkflowStatus.COMPLETED
    assert len(completed.tool_calls) == 1
    assert completed.tool_calls[0].outcome.state_changed is True
    assert workflow.audit_trace(completed.workflow_id).chain_valid is True


def test_approval_rejects_wrong_digest_and_stale_version(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
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

    with pytest.raises(ApprovalValidationError):
        workflow.approve(
            pending.workflow_id,
            ApprovalCommand(
                role="finance_manager",
                approved=True,
                proposal_digest="0" * 64,
                expected_state_version=pending.state_version,
            ),
            TEST_APPROVAL_PRINCIPAL,
        )
    with pytest.raises(WorkflowConflictError):
        workflow.approve(
            pending.workflow_id,
            ApprovalCommand(
                role="finance_manager",
                approved=True,
                proposal_digest=pending.approval_route.proposal_digest,
                expected_state_version=pending.state_version - 1,
            ),
            TEST_APPROVAL_PRINCIPAL,
        )


def test_rejected_approval_denies_without_executing_the_tool(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Finalize a human rejection without applying the proposed state change."""
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

    rejected = workflow.approve(
        pending.workflow_id,
        ApprovalCommand(
            role="finance_manager",
            approved=False,
            proposal_digest=pending.approval_route.proposal_digest,
            expected_state_version=pending.state_version,
        ),
        TEST_APPROVAL_PRINCIPAL,
    )

    assert rejected.status == WorkflowStatus.DENIED
    assert rejected.error_code == "approval_rejected"
    assert rejected.tool_calls == []


def test_multi_role_approval_survives_workflow_reconstruction(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    first_process = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(500_000),
    )
    pending = first_process.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 5000 refund on ticket TKT-1003 with all details",
        )
    )
    assert pending.status == WorkflowStatus.PENDING_APPROVAL
    assert {item.role for item in pending.approvals} == {
        "finance_manager",
        "fraud_reviewer",
    }
    assert pending.approval_route is not None

    reconstructed = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(500_000),
    )
    after_finance = reconstructed.approve(
        pending.workflow_id,
        ApprovalCommand(
            role="finance_manager",
            approved=True,
            proposal_digest=pending.approval_route.proposal_digest,
            expected_state_version=pending.state_version,
        ),
        TEST_APPROVAL_PRINCIPAL,
    )
    assert after_finance.status == WorkflowStatus.PENDING_APPROVAL

    completed = reconstructed.approve(
        pending.workflow_id,
        ApprovalCommand(
            role="fraud_reviewer",
            approved=True,
            proposal_digest=pending.approval_route.proposal_digest,
            expected_state_version=after_finance.state_version,
        ),
        TEST_APPROVAL_PRINCIPAL,
    )

    assert completed.status == WorkflowStatus.COMPLETED
    assert all(item.status.value == "approved" for item in completed.approvals)
    assert len(completed.tool_calls) == 1
