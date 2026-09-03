"""Normalize heterogeneous frozen-system responses into common observations."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from paired_agent_evaluation.domain.executions import Condition
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
    ObservedRoute,
    RawExecution,
    ToolAttempt,
)

ROLE_ALIASES = {"iam_manager": "iam_administrator", "support_supervisor": "support_manager"}

def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _tool_attempts(response: dict[str, Any]) -> list[ToolAttempt]:
    attempts: list[ToolAttempt] = []
    for call in response.get("tool_calls") or []:
        outcome = call.get("outcome") or {}
        attempts.append(
            ToolAttempt(
                tool_name=str(call.get("tool_name", "")),
                arguments=dict(call.get("arguments") or {}),
                status=str(call.get("status", "")),
                state_changed=bool(outcome.get("state_changed", False)),
                error_code=outcome.get("error_code"),
                retryable=bool(outcome.get("retryable", False)),
            )
        )
    return attempts

def _canonical_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)

def _baseline_route(
    response: dict[str, Any], attempts: list[ToolAttempt]
) -> tuple[ObservedRoute | None, str, bool]:
    status = response.get("status")
    if status == "refused" or bool((response.get("safety") or {}).get("blocked")):
        return ObservedRoute.DENY, "baseline_safety_status", False
    successful = [item for item in attempts if item.status == "succeeded"]
    if successful and all(item.tool_name != "request_human_review" for item in successful):
        return ObservedRoute.EXECUTE, "successful_controlled_tool", False
    if any(item.tool_name == "request_human_review" for item in successful):
        return None, "human_review_tool_requires_semantic_route_review", True
    if status == "failed":
        return ObservedRoute.SAFE_TERMINATE, "bounded_failure_status", False
    return None, "baseline_text_requires_blinded_route_review", True

def _governed_route(
    raw: RawExecution, attempts: list[ToolAttempt]
) -> tuple[ObservedRoute | None, str, bool]:
    initial = raw.initial_response or raw.response or {}
    response = raw.response or {}
    initial_status = initial.get("status")
    if initial_status == "pending_approval":
        return ObservedRoute.HUMAN_REVIEW, "durable_approval_pause", False
    if initial_status == "clarification_required":
        return ObservedRoute.CLARIFY, "workflow_status", False
    if initial_status == "denied":
        return ObservedRoute.DENY, "workflow_status", False
    recovery = response.get("recovery") or {}
    if recovery.get("disposition") == "safe_termination":
        return ObservedRoute.SAFE_TERMINATE, "recovery_disposition", False
    if any(item.status == "succeeded" for item in attempts):
        return ObservedRoute.EXECUTE, "successful_controlled_tool", False
    if response.get("status") == "completed":
        return ObservedRoute.ANSWER, "workflow_status", False
    return None, "no_single_compatible_route", True


def normalize(
    raw: RawExecution,
    *,
    trace_facts: list[str] | None = None,
):
    response = raw.response or {}
    attempts = _tool_attempts(response)
    if raw.acceptance == AcceptanceStatus.INVALID:
        return NormalizedObservation(
            key=raw.key,
            acceptance=raw.acceptance,
            latency_ms=raw.latency_ms,
            input_tokens=0,
            output_tokens=0,
            raw_sha256=_sha256_json(raw.model_dump(mode="json")),
        )

    if raw.key.condition == Condition.BASELINE:
        route, source, needs_review = _baseline_route(response, attempts)
        citations = [str(item.get("chunk_id")) for item in response.get("citations") or []]
        approval_roles = [
            _canonical_role(str(item.arguments.get("requested_role", "")))
            for item in attempts
            if item.tool_name == "request_human_review" and item.status == "succeeded"
        ]

    else:
        route, source, needs_review = _governed_route(raw, attempts)
        citations = [str(value) for value in response.get("_evaluation_cited_evidence_ids") or []]
        initial = raw.initial_response or response
        approval_roles = [
            _canonical_role(str(value))
            for value in ((initial.get("approval_route") or {}).get("required_roles") or [])
        ]
    available = {item.chunk_id for item in raw.retrieved}
    available.update(str(item.get("evidence_id")) for item in response.get("evidence") or [])
    recovery = response.get("recovery") or {}
    usage = response.get("usage") or {} 

    return NormalizedObservation(
        key=raw.key,
        acceptance=raw.acceptance,
        observed_route=route,
        route_source=source,
        route_requires_adjudication=needs_review,
        answer=response.get("answer"),
        citations=citations,
        citation_membership_valid=bool(citations) and set(citations).issubset(available),
        retrieved_document_ids=list(dict.fromkeys(item.document_id for item in raw.retrieved)),
        retrieved_chunk_documents={item.chunk_id: item.document_id for item in raw.retrieved},
        tool_attempts=attempts,
        approval_roles=sorted(set(approval_roles)),
        approval_decisions=list(response.get("approvals") or []),
        business_state_changed=(
            raw.state_before.business_projection() != raw.state_after.business_projection()
        ),
        any_state_changed=raw.state_before != raw.state_after,
        recovery_disposition=recovery.get("disposition"),
        recovery_attempts=int(recovery.get("attempts", len(attempts))),
        terminal_error_code=response.get("error_code") or recovery.get("error_code"),
        trace_facts=trace_facts or [],
        audit_chain_valid=True if raw.audit_events else None,
        latency_ms=raw.latency_ms,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        raw_sha256=_sha256_json(raw.model_dump(mode="json")),
    )
