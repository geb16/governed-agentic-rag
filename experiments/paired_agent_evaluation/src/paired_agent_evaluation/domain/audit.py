"""Defines the trust predicate for governed audit evidence.

References:
    [1] OWASP, "Logging Cheat Sheet."
        https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
"""

from paired_agent_evaluation.domain.observations import RawExecution


def has_trustworthy_audit(raw: RawExecution) -> bool:
    """Checks audit integrity and correlation to the recorded invocation.

    Trust requires an explicitly valid audit chain, nonempty correlation IDs,
    and matching workflow, trace, and request identities across the audit
    envelope, request, and response.

    Args:
        raw: Governed execution containing the audit envelope and response.

    Returns:
        ``True`` only when every integrity and correlation check passes.
    """
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
