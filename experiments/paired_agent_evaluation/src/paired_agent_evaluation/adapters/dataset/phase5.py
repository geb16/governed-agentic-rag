"""Read-only adapter for the content-addressed Phase 5 release."""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.integrity import verify_manifest
from app.evaluation.dataset.loader import load_cases, load_rubric
from app.evaluation.dataset.models import EvaluationCase, ScoringRubric


class Phase5Dataset:
    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root / "data" / "evaluation" / "phase5" / "v1"
        self.freeze_path = repository_root / "docs" / "phase-5-freeze-manifest.json"

    def verify(self) -> None:
        verify_manifest(self.root)

    def cases(self, split: DatasetSplit) -> list[EvaluationCase]:
        self.verify()
        return [case for case in load_cases(self.root / "cases.jsonl") if case.split == split]

    def rubric(self) -> ScoringRubric:
        self.verify()
        return load_rubric(self.root / "scoring-rubric.json")

    def freeze_identity(self) -> dict[str, object]:
        value: object = json.loads(self.freeze_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Phase 5 freeze manifest must be an object")
        return value
