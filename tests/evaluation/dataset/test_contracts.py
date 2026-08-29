# Validating release identity, distributions, and oracle coherence.

from collections import Counter

from app.evaluation.dataset import EvaluationCase, validate_dataset
from app.evaluation.dataset.enums import (
    DatasetSplit,
    ExpectedRoute,
    ScenarioCategory,
)


def test_release_has_frozen_count_and_distribution(cases: list[EvaluationCase]) -> None:
    validate_dataset(cases)
    assert Counter(case.split for case in cases) == {
        DatasetSplit.VALIDATION: 20,
        DatasetSplit.TEST: 80,
    }
    assert Counter(case.category for case in cases) == {
        ScenarioCategory.NORMAL: 17,
        ScenarioCategory.AMBIGUOUS: 16,
        ScenarioCategory.POLICY_SENSITIVE: 17,
        ScenarioCategory.HIGH_RISK: 17,
        ScenarioCategory.MISSING_INFORMATION: 16,
        ScenarioCategory.TOOL_FAILURE: 17,
    }


def test_all_routes_risks_tools_and_failure_modes_are_covered(
    cases: list[EvaluationCase],
) -> None:
    routes = {case.expected.route for case in cases}
    assert routes == set(ExpectedRoute)
    assert {case.expected.risk_level.value for case in cases} == {
        "low",
        "medium",
        "high",
        "critical",
    }
    assert {case.expected.expected_tool for case in cases if case.expected.expected_tool} == {
        "ticket_lookup",
        "policy_lookup",
        "response_drafter",
        "update_ticket_status",
        "issue_refund",
        "change_access_role",
        "request_human_review",
    }
    assert {plan.mode.value for case in cases for plan in case.fixture.fault_plans} == {
        "transient_error",
        "timeout",
        "permanent_error",
    }
