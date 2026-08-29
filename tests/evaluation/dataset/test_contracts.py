# Validating release identity, distributions, and oracle coherence.

from collections import Counter

from app.evaluation.dataset import EvaluationCase, validate_dataset
from app.evaluation.dataset.enums import (
    DatasetSplit,
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

