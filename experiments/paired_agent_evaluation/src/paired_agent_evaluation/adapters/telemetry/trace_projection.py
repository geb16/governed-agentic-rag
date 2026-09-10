"""Projects comparable trace facts from retained execution evidence.

Baseline facts come from its response and recorded retrieval activity. Governed
stage and decision facts are emitted only when the retained audit chain passes
integrity checks, preventing untrusted telemetry from influencing comparison.
"""

from __future__ import annotations

from paired_agent_evaluation.domain.audit import has_trustworthy_audit
from paired_agent_evaluation.domain.executions import Condition
from paired_agent_evaluation.domain.observations import RawExecution

STAGE_FACT = {
    "task_classification": "classification",
    "knowledge_retrieval": "retrieval_evidence",
    "proposed_action_generation": "proposed_action",
    "risk_checking": "risk_decision",
    "approval_routing": "approval_route",
    "retry_recovery": "recovery_decision",
    "final_response_audit": "final_outcome",
}


def project_trace_facts(raw: RawExecution) -> list[str]:
    """Derives supported semantic facts from one raw execution.

    Executions without a response produce no facts. Governed executions also
    require a trustworthy audit chain; baseline executions use response tool
    calls because they do not produce governed audit events. Duplicate facts are
    removed and the result is sorted for deterministic reporting.

    Args:
        raw: Retained execution evidence to project.

    Returns:
        Deterministically ordered semantic fact names supported by the evidence.
    """
    if raw.response is None:
        return []
    if raw.key.condition == Condition.GOVERNED and not has_trustworthy_audit(raw):
        return []
    facts = {"request_identity", "final_outcome"}
    if raw.retrieval_call_count:
        facts.add("retrieval_evidence")
    tool_calls = raw.response.get("tool_calls") or []
    if tool_calls:
        facts.update({"proposed_action", "tool_attempt"})
    if raw.key.condition == Condition.BASELINE:
        if any(call.get("tool_name") == "request_human_review" for call in tool_calls):
            facts.add("approval_route")
        return sorted(facts)

    for event in raw.audit_events:
        if event.get("event_type") == "stage_completed":
            fact = STAGE_FACT.get(str(event.get("stage")))
            if fact:
                facts.add(fact)
        if event.get("event_type") == "approval_recorded":
            facts.add("approval_decision")
        if event.get("event_type") == "tool_attempted":
            facts.add("tool_attempt")
    return sorted(facts)
