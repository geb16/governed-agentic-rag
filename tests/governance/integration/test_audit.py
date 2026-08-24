from __future__ import annotations

import sqlite3

import pytest

from app.audit.schemas import AuditEventType
from app.audit.sqlite import SqliteAuditRepository
from app.audit.verifier import verify_hash_chain
from app.governance.contracts import (
    GovernedRequest,
    WorkflowStatus,
)
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from tests.governance.support import (
    ScriptedGovernanceModel,
    audit_integrity_key,
    build_governed_workflow,
)


def test_audit_chain_is_complete_and_database_enforced_append_only(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
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
    trace = workflow.audit_trace(response.workflow_id)

    assert response.status == WorkflowStatus.COMPLETED
    assert trace.chain_valid is True
    assert [event.sequence_number for event in trace.events] == list(
        range(1, len(trace.events) + 1)
    )
    assert trace.events[0].event_type == AuditEventType.WORKFLOW_STARTED
    assert trace.events[-1].event_type == AuditEventType.WORKFLOW_COMPLETED

    connection = sqlite3.connect(settings.synthetic_database_path)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                """
                UPDATE governance_audit_events
                SET details_json = '{}'
                WHERE workflow_id = ?
                """,
                (response.workflow_id,),
            )
    finally:
        connection.close()


def test_audit_verifier_rejects_empty_wrong_key_and_representative_tampering(
    settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Reject absent events, invalid integrity keys, and representative chain tampering."""

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
    events = workflow.audit_trace(response.workflow_id).events
    key = audit_integrity_key(settings)

    assert verify_hash_chain([], key=key) is False
    assert verify_hash_chain(events, key=b"incorrect-integrity-key") is False
    tampered_chains = (
        [events[0].model_copy(update={"schema_version": 999}), *events[1:]],
        [events[0].model_copy(update={"sequence_number": 99}), *events[1:]],
        [events[0].model_copy(update={"trace_id": "trace_tampered"}), *events[1:]],
        [events[0].model_copy(update={"previous_event_hash": "0" * 64}), *events[1:]],
    )
    assert all(verify_hash_chain(chain, key=key) is False for chain in tampered_chains)


def test_audit_repository_rejects_unknown_schema_version(settings, repository) -> None:
    """Require an explicit migration instead of silently relabelling an existing schema."""

    audit = SqliteAuditRepository(
        settings.synthetic_database_path,
        integrity_key=audit_integrity_key(settings),
    )
    audit.initialize()
    with sqlite3.connect(settings.synthetic_database_path) as connection:
        connection.execute(
            "UPDATE schema_metadata SET value = '999' WHERE key = 'governance_audit_schema_version'"
        )

    with pytest.raises(RuntimeError, match="Unsupported governance audit schema version"):
        audit.initialize()
