"""Provide session-scoped fixtures for checked-in Phase 5 artifacts."""

from pathlib import Path

import pytest

from app.evaluation.dataset import EvaluationCase, ScoringRubric, load_cases, load_rubric

DATA_ROOT = Path("data/evaluation/phase5/v1")


@pytest.fixture(scope="session")
def cases() -> list[EvaluationCase]:
    """Load all checked-in cases through the strict contract.

    Returns:
        Evaluation cases shared by the dataset test session.
    """
    return load_cases(DATA_ROOT / "cases.jsonl")


@pytest.fixture(scope="session")
def rubric() -> ScoringRubric:
    """Load the checked-in scoring rubric through its strict contract.

    Returns:
        Scoring rubric shared by the dataset test session.
    """
    return load_rubric(DATA_ROOT / "scoring-rubric.json")
