# Reusable fixtures for checked-in Phase-5 artifacts.

from pathlib import Path

import pytest

from app.evaluation.dataset import EvaluationCase, ScoringRubric, load_cases, load_rubric

DATA_ROOT = Path("data/evaluation/phase5/v1")


@pytest.fixture(scope="session")
def cases() -> list[EvaluationCase]:
    """Load all checked-in cases once through the strict contract."""
    return load_cases(DATA_ROOT / "cases.jsonl")


@pytest.fixture(scope="session")
def rubric() -> ScoringRubric:
    """Load the frozen scoring rubric once."""
    return load_rubric(DATA_ROOT / "scoring-rubric.json")
