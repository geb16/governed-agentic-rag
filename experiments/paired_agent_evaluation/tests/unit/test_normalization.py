"""Verify canonical observation projection from condition-specific executions."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

from paired_agent_evaluation.adapters.telemetry import project_trace_facts
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    ObservedRoute,
    RawExecution,
    RetrievedEvidence,
)


def _raw_execution(condition: Condition, response: Mapping[str, object]) -> RawExecution:
    """Build an accepted execution for normalization tests."""
    recorded_at = datetime(2025, 1, 1, tzinfo=UTC)
    return RawExecution(
        key=ExecutionKey(case_id="case_eval_0001", repetition=1, condition=condition),
        acceptance=AcceptanceStatus.ACCEPTED,
        request_accepted=True,
        started_at=recorded_at,
        completed_at=recorded_at,
        latency_ms=1,
        request={"query": "question"},
        response=dict(response),
        retrieved=[
            RetrievedEvidence(
                chunk_id="chunk-1",
                document_id="policy-1",
                title="Policy",
                content="Evidence",
                content_sha256="a" * 64,
                score=1,
            )
        ],
        state_before=BusinessState(),
        state_after=BusinessState(),
    )


def test_normalization_preserves_chunk_level_context_and_trace_projection() -> None:
    """Preserve retrieval provenance and trusted trace facts in canonical form."""
    response = {
        "status": "completed",
        "answer": "Evidence",
        "_evaluation_cited_evidence_ids": ["chunk-1"],
    }
    observation = normalize(
        _raw_execution(Condition.GOVERNED, response),
        trace_facts=["classification_recorded"],
    )
    assert observation.observed_route == ObservedRoute.ANSWER
    assert observation.citation_membership_valid is True
    assert observation.retrieved_chunk_documents == {"chunk-1": "policy-1"}
    assert observation.trace_facts == ["classification_recorded"]


def test_normalization_preserves_audit_integrity_and_requires_correlation() -> None:
    """Expose audit integrity only when invocation identifiers correlate."""
    raw = _raw_execution(
        Condition.GOVERNED,
        {
            "status": "completed",
            "workflow_id": "workflow-1",
            "request_id": "request-1",
            "trace_id": "trace-1",
        },
    ).model_copy(
        update={
            "request": {"request_id": "request-1"},
            "audit_chain_valid": True,
            "audit_workflow_id": "workflow-1",
            "audit_trace_id": "trace-1",
            "audit_request_id": "request-1",
        }
    )

    observation = normalize(raw)

    assert observation.audit_chain_valid is True
    assert observation.audit_correlation_valid is True

    tampered = raw.model_copy(update={"audit_chain_valid": False})
    assert normalize(tampered).audit_chain_valid is False
    assert normalize(tampered).audit_correlation_valid is False

    assert project_trace_facts(tampered) == []


@pytest.mark.parametrize(
    ("response", "route", "needs_review"),
    [
        ({"status": "refused", "safety": {"blocked": True}}, ObservedRoute.DENY, False),
        ({"status": "failed"}, ObservedRoute.SAFE_TERMINATE, False),
        (
            {
                "status": "completed",
                "tool_calls": [
                    {"tool_name": "ticket_update", "status": "succeeded", "outcome": {}}
                ],
            },
            ObservedRoute.EXECUTE,
            False,
        ),
        ({"status": "completed", "answer": "Text"}, None, True),
    ],
)
def test_baseline_route_normalization(
    response: dict[str, object],
    route: ObservedRoute | None,
    needs_review: bool,
) -> None:
    """Map explicit baseline outcomes and defer ambiguous answers to review."""
    observation = normalize(_raw_execution(Condition.BASELINE, response))
    assert observation.observed_route == route
    assert observation.route_requires_adjudication is needs_review
