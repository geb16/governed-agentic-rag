"""Validate cross-case invariants and frozen-tool coverage for Phase 5.

Enforces release-wide rules a single EvaluationCase cannot check alone:
unique identifiers, the frozen split/category distribution, minimal-pair
completeness, and full validation-split coverage of every governed
dimension (route, tool, intent, risk, decision, failure mode).
Core:
    - validate_dataset(): the single entry point for all release invariants.
References:
    [1] NIST, AI RMF 1.0 (NIST AI 100-1), 2023. https://doi.org/10.6028/NIST.AI.100-1
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from app.domain.support import FailureMode
from app.evaluation.dataset.enums import (
    DatasetSplit,
    ExpectedRiskLevel,
    ExpectedRoute,
    InteractionChannel,
    ReviewDecision,
    ScenarioCategory,
)
from app.evaluation.dataset.models import EvaluationCase
from app.tools.access_role import ChangeAccessRoleArguments
from app.tools.human_review import HumanReviewArguments
from app.tools.policy_lookup import PolicyLookupArguments
from app.tools.refund import IssueRefundArguments
from app.tools.response_drafter import ResponseDrafterArguments
from app.tools.ticket_lookup import TicketLookupArguments
from app.tools.ticket_update import TicketUpdateArguments

EXPECTED_CASE_COUNT = 100
EXPECTED_SPLITS = {DatasetSplit.VALIDATION: 20, DatasetSplit.TEST: 80}
EXPECTED_CATEGORIES = {
    ScenarioCategory.NORMAL: 17,
    ScenarioCategory.AMBIGUOUS: 16,
    ScenarioCategory.POLICY_SENSITIVE: 17,
    ScenarioCategory.HIGH_RISK: 17,
    ScenarioCategory.MISSING_INFORMATION: 16,
    ScenarioCategory.TOOL_FAILURE: 17,
}
EXPECTED_VALIDATION_CHANNELS = dict.fromkeys(InteractionChannel, 5)
EXPECTED_INTENTS = {
    "access_change",
    "data_deletion",
    "human_escalation",
    "information",
    "other",
    "refund",
    "security_attack",
    "ticket_lookup",
    "ticket_update",
}

_TOOL_INPUTS: dict[str, type[BaseModel]] = {
    "policy_lookup": PolicyLookupArguments,
    "ticket_lookup": TicketLookupArguments,
    "response_drafter": ResponseDrafterArguments,
    "update_ticket_status": TicketUpdateArguments,
    "issue_refund": IssueRefundArguments,
    "change_access_role": ChangeAccessRoleArguments,
    "request_human_review": HumanReviewArguments,
}


def validate_dataset(cases: list[EvaluationCase]) -> None:
    """Validate release-wide identity, distribution, and coverage invariants.

    Args:
        cases: Complete candidate case sequence.

    Raises:
        ValueError: If identities, labels, tool contracts, or coverage drift.
    """
    if len(cases) != EXPECTED_CASE_COUNT:
        raise ValueError(f"Expected {EXPECTED_CASE_COUNT} cases, found {len(cases)}")
    ids = [case.case_id for case in cases]
    request_ids = [case.request.request_id for case in cases]
    queries = [case.request.query.casefold() for case in cases]
    if len(set(ids)) != len(ids) or len(set(request_ids)) != len(request_ids):
        raise ValueError("Case and request identifiers must be unique")
    if len(set(queries)) != len(queries):
        raise ValueError("Evaluation queries must be unique")
    minimal_pair_counts = Counter(
        case.minimal_pair_id for case in cases if case.minimal_pair_id is not None
    )
    singleton_pairs = sorted(pair_id for pair_id, count in minimal_pair_counts.items() if count < 2)
    if singleton_pairs:
        raise ValueError(
            "Minimal-pair groups require at least two cases: " + ", ".join(singleton_pairs)
        )
    if Counter(case.split for case in cases) != EXPECTED_SPLITS:
        raise ValueError("Dataset split distribution does not match the frozen design")
    if Counter(case.category for case in cases) != EXPECTED_CATEGORIES:
        raise ValueError("Scenario distribution does not match the frozen design")

    validation_cases = [case for case in cases if case.split == DatasetSplit.VALIDATION]
    if Counter(case.channel for case in validation_cases) != EXPECTED_VALIDATION_CHANNELS:
        raise ValueError("Validation channels must be evenly represented")
    if {case.expected.route for case in validation_cases} != set(ExpectedRoute):
        raise ValueError("Validation cases must cover every expected route")
    if {
        case.expected.expected_tool
        for case in validation_cases
        if case.expected.expected_tool is not None
    } != set(_TOOL_INPUTS):
        raise ValueError("Validation cases must cover every allowlisted tool")
    if {plan.mode for case in validation_cases for plan in case.fixture.fault_plans} != set(
        FailureMode
    ):
        raise ValueError("Validation cases must cover every deterministic failure mode")
    if {case.expected.intent for case in validation_cases} != EXPECTED_INTENTS:
        raise ValueError("Validation cases must cover every major intent")
    if {case.expected.risk_level for case in validation_cases} != set(ExpectedRiskLevel):
        raise ValueError("Validation cases must cover every expected risk level")
    if {
        decision.decision for case in validation_cases for decision in case.expected.human_decisions
    } != set(ReviewDecision):
        raise ValueError("Validation cases must cover approval and rejection outcomes")

    for case in cases:
        expected_tool = case.expected.expected_tool
        if expected_tool is not None:
            model = _TOOL_INPUTS.get(expected_tool)
            if model is None:
                raise ValueError(f"{case.case_id} names an unallowlisted tool")
            if case.expected.tool_arguments:
                model.model_validate(case.expected.tool_arguments)
        for plan in case.fixture.fault_plans:
            if plan.tool_name not in _TOOL_INPUTS:
                raise ValueError(f"{case.case_id} injects a fault into an unknown tool")
