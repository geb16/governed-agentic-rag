"""Load versioned evaluation artifacts through strict domain contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.evaluation.dataset.models import EvaluationCase, ScoringRubric


def load_cases(path: Path) -> list[EvaluationCase]:
    """Load strictly validated JSON Lines cases in file order.

    Args:
        path: UTF-8 JSON Lines artifact to read.

    Returns:
        Evaluation cases in their declared release order.

    Raises:
        ValueError: If a line is malformed or violates the case contract.
    """
    cases: list[EvaluationCase] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload: Any = json.loads(raw)
            cases.append(EvaluationCase.model_validate(payload))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Invalid evaluation case at {path}:{line_number}") from exc
    return cases


def load_rubric(path: Path) -> ScoringRubric:
    """Load a strictly validated scoring rubric.

    Args:
        path: UTF-8 rubric JSON path.

    Returns:
        Versioned scoring and statistical protocol.

    Raises:
        ValueError: If the JSON or rubric contract is invalid.
    """
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    return ScoringRubric.model_validate(payload)
