"""Boundary and exception cases grounded only in the frozen synthetic policies."""

# Natural-language benchmark prompts are kept as single literals for reviewability.
# ruff: noqa: E501

from app.evaluation.dataset.enums import (
    ExpectedRiskLevel as Risk,
)
from app.evaluation.dataset.enums import (
    ExpectedRoute as Route,
)
from app.evaluation.dataset.enums import (
    ExpectedSensitivity as Sensitivity,
)
from app.evaluation.dataset.enums import (
    ExpectedTaskType as TaskType,
)
from app.evaluation.dataset.enums import (
    ScenarioCategory,
)
from app.evaluation.dataset.generation.common import (
    make_case,
    refund_arguments,
)
from app.evaluation.dataset.models import EvaluationCase


def cases() -> list[EvaluationCase]:
    """Return 17 policy-boundary cases, including controlled minimal pairs."""
    c = ScenarioCategory.POLICY_SENSITIVE
    return [
        make_case(
            34,
            c,
            "Refund immediately below approval threshold",
            "Issue GBP 499.99 on TKT-1001, received 7 days ago, reason code OUTAGE, key eval0034refund.",
            route=Route.EXECUTE,
            intent="refund",
            task_type=TaskType.STATE_CHANGING,
            sensitivity=Sensitivity.MODERATE,
            risk=Risk.MEDIUM,
            tool="issue_refund",
            arguments=refund_arguments(34, 49_999),
            documents=["refund_policy"],
            ticket_status="open",
            ticket_category="refund",
            state_change=True,
            pair="pair_refund_finance_threshold",
            sources=["openai-support", "openai-contextual-evals"],
        ),

    ]
