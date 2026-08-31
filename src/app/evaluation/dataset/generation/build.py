"""Assemble and validate the complete version 1.0.0 case sequence."""

from app.evaluation.dataset.generation import (
    ambiguous,
    high_risk,
    missing_information,
    normal,
    policy_sensitive,
    tool_failure,
)
from app.evaluation.dataset.models import EvaluationCase
from app.evaluation.dataset.validation import validate_dataset


def build_cases() -> list[EvaluationCase]:
    """Assemble and validate all cases in stable identifier order.

    Returns:
        Complete version 1.0.0 evaluation case sequence.

    Raises:
        ValueError: If any cross-case invariant or coverage requirement fails.
    """
    result = [
        *normal.cases(),
        *ambiguous.cases(),
        *policy_sensitive.cases(),
        *high_risk.cases(),
        *missing_information.cases(),
        *tool_failure.cases(),
    ]
    validate_dataset(result)
    return result
