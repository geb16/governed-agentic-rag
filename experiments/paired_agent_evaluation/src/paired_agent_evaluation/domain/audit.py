"""Provider-neutral audit integrity rules for governed observations."""

from paired_agent_evaluation.domain.observations import RawExecution


def has_trustworthy_audit(raw: RawExecution) -> bool:
    """Require a valid chain correlated to the exact governed invocation."""
    response = raw.response or {}
    identifiers = (
        raw.audit_workflow_id,
        response.get("workflow_id"),
        raw.audit_trace_id,
        response.get("trace_id"),
        raw.audit_request_id,
        raw.request.get("request_id"),
        response.get("request_id"),
    )
    return (
        raw.audit_chain_valid is True
        and all(isinstance(value, str) and bool(value) for value in identifiers)
        and raw.audit_workflow_id == response["workflow_id"]
        and raw.audit_trace_id == response["trace_id"]
        and raw.audit_request_id == raw.request["request_id"] == response["request_id"]
    )
