from datetime import UTC, datetime

from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    ObservedRoute,
    RawExecution,
    RetrievedEvidence,
)


def _raw(condition: Condition, response: dict) -> RawExecution:
    now = datetime.now(UTC)
    return RawExecution(
        key=ExecutionKey(case_id="case_eval_0001", repetition=1, condition=condition),
        acceptance=AcceptanceStatus.ACCEPTED,
        request_accepted=True,
        started_at=now,
        completed_at=now,
        latency_ms=1,
        request={"query": "question"},
        response=response,
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
    response = {
        "status": "completed",
        "answer": "Evidence",
        "_evaluation_cited_evidence_ids": ["chunk-1"],
    }
    observation = normalize(
        _raw(Condition.GOVERNED, response), trace_facts=["classification_recorded"]
    )
    assert observation.observed_route == ObservedRoute.ANSWER
    assert observation.citation_membership_valid is True
    assert observation.retrieved_chunk_documents == {"chunk-1": "policy-1"}
    assert observation.trace_facts == ["classification_recorded"]
