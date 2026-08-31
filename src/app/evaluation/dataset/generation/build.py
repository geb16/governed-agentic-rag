"""Assemble and validate the complete version 1.0.0 case sequence.

Concatenates all six category modules in the fixed, stable identifier
order the release depends on, then runs validate_dataset() before
returning so a broken invariant fails at build time, not release time.
Core:
    - build_cases(): the single source of truth for the 100-case sequence.
References:
    [1] NIST, AI RMF 1.0 (NIST AI 100-1), 2023. https://doi.org/10.6028/NIST.AI.100-1
"""

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
