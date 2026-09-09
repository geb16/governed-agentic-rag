from datetime import UTC, datetime

from paired_agent_evaluation.domain.audit import has_trustworthy_audit

from paired_agent_evaluation.adapters.telemetry import project_trace_facts
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)


def _raw() -> RawExecution:
    now = datetime.now(UTC)
    return RawExecution(
        key=ExecutionKey(case_id="case_eval_0001", repetition=1, condition=Condition.GOVERNED),
        acceptance=AcceptanceStatus.ACCEPTED,
        request_accepted=True,
        started_at=now,
        completed_at=now,
        latency_ms=1,
        request={"request_id": "req-1", "query": "question"},
        response={
            "request_id": "req-1",
            "workflow_id": "wf-1",
            "trace_id": "trace-1",
            "status": "completed",
        },
        state_before=BusinessState(),
        state_after=BusinessState(),
        audit_events=[
            {
                "event_type": "stage_completed",
                "stage": "task_classification",
            }
        ],
        audit_chain_valid=True,
        audit_workflow_id="wf-1",
        audit_trace_id="trace-1",
        audit_request_id="req-1",
    )


def test_valid_audit_envelope_supports_trace_evidence() -> None:
    """Accept trace facts only when chain and invocation identities agree."""
    raw = _raw()

    assert has_trustworthy_audit(raw) is True
    assert normalize(raw).audit_correlation_valid is True
    assert "classification" in project_trace_facts(raw)

