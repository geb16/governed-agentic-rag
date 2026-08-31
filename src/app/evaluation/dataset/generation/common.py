"""Factories that keep hand-authored scenario modules concise and consistent.

Centralizes what every category module repeats: deterministic case/request
IDs, split assignment, channel rotation, and rationale text. Category
modules supply only the scenario-specific route, intent, and oracle fields.
Core:
    - make_case(): builds one EvaluationCase from labelled scenario fields.
    - fault(): builds a bounded deterministic FaultPlan.
    - refund_arguments(), review_arguments(): valid tool-argument builders.
References:
    [1] Gamma et al., Design Patterns (Factory Method), Addison-Wesley, 1994.
    [2] Pydantic, "Configuration." https://docs.pydantic.dev/latest/concepts/config/
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.support import (
    AccessAccountRecord,
    FailureMode,
    FaultPlan,
    SyntheticCaseFixture,
    TicketRecord,
)
from app.domain.tasks import TaskRequest
from app.evaluation.dataset.enums import (
    DatasetSplit,
    ExpectedRiskLevel,
    ExpectedRoute,
    ExpectedSensitivity,
    ExpectedTaskType,
    InteractionChannel,
    RecoveryExpectation,
    ReviewDecision,
    ScenarioCategory,
    TraceFact,
)
from app.evaluation.dataset.models import (
    EvaluationCase,
    ExpectedBehavior,
    ExpectedRecovery,
    HumanDecision,
)

_VALIDATION_NUMBERS = {
    2,
    9,
    15,
    17,
    19,
    21,
    22,
    34,
    43,
    44,
    56,
    57,
    64,
    80,
    81,
    82,
    94,
    95,
    99,
    100,
}
_CHANNELS = tuple(InteractionChannel)


def fault(tool_name: str, mode: str, failures: int, code: str) -> FaultPlan:
    """Create a bounded deterministic tool-failure fixture.

    Args:
        tool_name: Allowlisted tool receiving the injected failure.
        mode: Serialized failure mode.
        failures: Number of consecutive failed attempts.
        code: Stable synthetic error code.

    Returns:
        Validated fault plan for an isolated case.

    Raises:
        ValueError: If the failure mode or bounds are invalid.
    """
    return FaultPlan(
        tool_name=tool_name,
        mode=FailureMode(mode),
        failures=failures,
        error_code=code,
    )


def make_case(
    number: int,
    category: ScenarioCategory,
    title: str,
    query: str,
    *,
    route: ExpectedRoute,
    intent: str,
    task_type: ExpectedTaskType,
    sensitivity: ExpectedSensitivity,
    risk: ExpectedRiskLevel,
    tool: str | None = None,
    arguments: dict[str, Any] | None = None,
    approval_roles: Sequence[str] = (),
    human_decisions: Sequence[tuple[str, str]] = (),
    clarification_fields: Sequence[str] = (),
    denial_code: str | None = None,
    documents: Sequence[str] = (),
    risk_flags: Sequence[str] = (),
    tags: Sequence[str] = (),
    pair: str | None = None,
    ticket_status: str | None = None,
    ticket_category: str = "customer_support",
    ticket_summary: str = "Synthetic support request awaiting handling.",
    account_role: str | None = None,
    fault_plans: Sequence[FaultPlan] = (),
    recovery: RecoveryExpectation = RecoveryExpectation.NOT_APPLICABLE,
    attempts: int = 0,
    error_code: str | None = None,
    state_change: bool = False,
    sources: Sequence[str] = ("nist-ai-rmf", "openai-contextual-evals"),
) -> EvaluationCase:
    """Build one isolated request, fixture, and gold behavior oracle.

    Args:
        number: Stable numeric identity used for case and request IDs.
        category: Primary mutually exclusive scenario stratum.
        title: Reviewer-facing case title.
        query: Exact synthetic request presented to both systems.
        route: Pre-adjudicated observable outcome.
        intent: Normalized task intent.
        task_type: Expected operational effect.
        sensitivity: Expected information sensitivity.
        risk: Expected risk classification.
        tool: Expected allowlisted tool, when applicable.
        arguments: Material gold tool arguments.
        approval_roles: Accountable roles required before execution.
        human_decisions: Ordered reviewer roles and deterministic decisions.
        clarification_fields: Material inputs absent from the request.
        denial_code: Stable reason for a prohibited or unsupported request.
        documents: Frozen knowledge documents required for grounding.
        risk_flags: Expected policy and security findings.
        tags: Secondary analysis labels.
        pair: Optional controlled-contrast group identifier.
        ticket_status: Optional initial synthetic ticket status.
        ticket_category: Initial synthetic ticket category.
        ticket_summary: Initial synthetic ticket summary.
        account_role: Optional initial synthetic access role.
        fault_plans: Deterministic tool failures injected for the case.
        recovery: Gold recovery or safe-termination outcome.
        attempts: Expected tool-attempt count.
        error_code: Expected terminal failure code.
        state_change: Whether the authorized outcome mutates business state.
        sources: Registry identifiers informing scenario design.

    Returns:
        Strict evaluation case with deterministic split, channel, and trace oracle.

    Raises:
        ValueError: If any request, fixture, recovery, or route contract is invalid.
    """
    case_id = f"case_eval_{number:04d}"
    fixture = SyntheticCaseFixture(
        case_id=case_id,
        tickets=(
            [
                TicketRecord(
                    ticket_id="TKT-1001",
                    status=ticket_status,
                    category=ticket_category,
                    summary=ticket_summary,
                    version=1,
                )
            ]
            if ticket_status
            else []
        ),
        access_accounts=(
            [AccessAccountRecord(subject_id="USR-1001", role=account_role, version=1)]
            if account_role
            else []
        ),
        fault_plans=list(fault_plans),
    )
    decisions = [
        HumanDecision(role=role, decision=ReviewDecision(decision))
        for role, decision in human_decisions
    ]
    trace_facts = _trace_facts(
        tool=tool,
        decisions=decisions,
        has_fault=bool(fault_plans),
    )
    return EvaluationCase(
        case_id=case_id,
        split=(DatasetSplit.VALIDATION if number in _VALIDATION_NUMBERS else DatasetSplit.TEST),
        category=category,
        channel=_CHANNELS[(number - 1) % len(_CHANNELS)],
        title=title,
        request=TaskRequest(
            request_id=f"req_eval_{number:04d}",
            case_id=case_id,
            requester_id=f"synthetic_requester_{((number - 1) % 12) + 1:02d}",
            query=query,
        ),
        fixture=fixture,
        expected=ExpectedBehavior(
            route=route,
            intent=intent,
            task_type=task_type,
            sensitivity=sensitivity,
            risk_level=risk,
            expected_tool=tool,
            tool_arguments=arguments or {},
            state_change_expected=state_change,
            approval_roles=list(approval_roles),
            human_decisions=decisions,
            clarification_fields=list(clarification_fields),
            denial_reason_code=denial_code,
            retrieval_documents=list(documents),
            risk_flags=list(risk_flags),
            recovery=ExpectedRecovery(
                expectation=recovery,
                expected_attempts=attempts,
                expected_error_code=error_code,
            ),
            required_trace_facts=trace_facts,
        ),
        label_rationale=_label_rationale(
            route=route,
            tool=tool,
            roles=approval_roles,
            fields=clarification_fields,
            denial_code=denial_code,
            recovery=recovery,
        ),
        tags=[category.value, intent, *tags],
        minimal_pair_id=pair,
        design_source_ids=list(sources),
    )


def _trace_facts(
    *,
    tool: str | None,
    decisions: Sequence[HumanDecision],
    has_fault: bool,
) -> list[TraceFact]:
    """Derive required semantic trace facts from observable case behavior.

    Args:
        tool: Expected tool name, if execution is observable.
        decisions: Deterministic human decisions to replay.
        has_fault: Whether recovery behavior must be traceable.

    Returns:
        Ordered trace facts required for completeness scoring.
    """
    facts = [
        TraceFact.REQUEST_IDENTITY,
        TraceFact.CLASSIFICATION,
        TraceFact.RETRIEVAL_EVIDENCE,
        TraceFact.PROPOSED_ACTION,
        TraceFact.RISK_DECISION,
        TraceFact.APPROVAL_ROUTE,
    ]
    if decisions:
        facts.append(TraceFact.APPROVAL_DECISION)
    if tool and not any(item.decision == ReviewDecision.REJECT for item in decisions):
        facts.append(TraceFact.TOOL_ATTEMPT)
    if has_fault:
        facts.append(TraceFact.RECOVERY_DECISION)
    facts.append(TraceFact.FINAL_OUTCOME)
    return facts


def _label_rationale(
    *,
    route: ExpectedRoute,
    tool: str | None,
    roles: Sequence[str],
    fields: Sequence[str],
    denial_code: str | None,
    recovery: RecoveryExpectation,
) -> str:
    """Render a concise explanation of the pre-adjudicated route.

    Args:
        route: Gold outcome route.
        tool: Expected tool, when applicable.
        roles: Roles required for human review.
        fields: Inputs required before safe execution.
        denial_code: Stable prohibition reason.
        recovery: Expected terminal recovery behavior.

    Returns:
        Reviewer-facing rationale grounded in the case labels.
    """
    if route == ExpectedRoute.ANSWER:
        return "The request is read-only and can be answered from the frozen approved knowledge."
    if route == ExpectedRoute.EXECUTE:
        return f"The request supplies the material inputs for the allowed {tool} capability."
    if route == ExpectedRoute.HUMAN_REVIEW:
        return "Policy requires accountable review before action by: " + ", ".join(roles)
    if route == ExpectedRoute.CLARIFY:
        return "Safe execution requires the missing or authoritative fields: " + ", ".join(fields)
    if route == ExpectedRoute.DENY:
        return f"The request is prohibited or unsupported under the {denial_code} rule."
    return f"The injected failure must end as {recovery.value} without changing business state."


def refund_arguments(number: int, amount_minor: int, currency: str = "GBP") -> dict[str, Any]:
    """Create valid refund arguments with a stable idempotency key.

    Args:
        number: Case number embedded in the idempotency key.
        amount_minor: Refund value in minor currency units.
        currency: ISO-style currency code; defaults to GBP.

    Returns:
        Material arguments accepted by the simulated refund tool.
    """
    return {
        "ticket_id": "TKT-1001",
        "amount_minor": amount_minor,
        "currency": currency,
        "idempotency_key": f"eval{number:04d}refund",
    }


def review_arguments(number: int, role: str, reason: str) -> dict[str, Any]:
    """Create a deterministic human-review request payload.

    Args:
        number: Case number embedded in the idempotency key.
        role: Accountable reviewer role.
        reason: Reviewer-facing escalation reason.

    Returns:
        Material arguments accepted by the simulated review tool.
    """
    return {
        "ticket_id": "TKT-1001",
        "reason": reason,
        "requested_role": role,
        "idempotency_key": f"eval{number:04d}review",
    }
