"""Integration coverage for governed tool-failure recovery."""

from __future__ import annotations

from app.audit.schemas import AuditEventType
from app.domain.support import FailureMode, FaultPlan
from app.governance.contracts import GovernedRequest, WorkflowStatus
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from tests.governance.integration.workflow_support import refund_model
from tests.governance.support import build_governed_workflow


def test_retry_recovery_is_visible_in_audit_trace(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    repository.set_fault_plan(
        "case_default",
        FaultPlan(
            tool_name="issue_refund",
            mode=FailureMode.TIMEOUT,
            failures=1,
            error_code="synthetic_timeout",
        ),
    )
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(10_000),
    )

    response = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 100 refund on ticket TKT-1003 with all details",
        )
    )
    trace = workflow.audit_trace(response.workflow_id)

    assert response.status == WorkflowStatus.COMPLETED
    assert response.recovery is not None
    assert response.recovery.disposition.value == "retried_and_succeeded"
    assert len(response.tool_calls) == 2
    assert sum(event.event_type == AuditEventType.RETRY_SCHEDULED for event in trace.events) == 1


def test_non_retryable_tool_failure_terminates_safely_without_retry(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Persist and audit one permanent failure without repeating the side effect."""
    repository.set_fault_plan(
        "case_default",
        FaultPlan(
            tool_name="issue_refund",
            mode=FailureMode.PERMANENT_ERROR,
            failures=1,
            error_code="synthetic_permanent_failure",
        ),
    )
    workflow = build_governed_workflow(
        settings=settings,
        retriever=retriever,
        repository=repository,
        model=refund_model(10_000),
    )

    response = workflow.invoke(
        GovernedRequest(
            requester_id="support-user",
            query="Issue a GBP 100 refund on ticket TKT-1003 with all details",
        )
    )
    trace = workflow.audit_trace(response.workflow_id)

    assert response.status == WorkflowStatus.FAILED
    assert response.error_code == "synthetic_permanent_failure"
    assert response.recovery is not None
    assert response.recovery.disposition.value == "safe_termination"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].outcome.state_changed is False
    assert not any(event.event_type == AuditEventType.RETRY_SCHEDULED for event in trace.events)
    assert trace.chain_valid is True
