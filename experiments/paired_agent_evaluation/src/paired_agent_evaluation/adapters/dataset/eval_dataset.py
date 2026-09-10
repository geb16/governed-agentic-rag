"""Provides verified, read-only access to the frozen Phase 5 dataset.

The adapter resolves release artifacts from a repository root and verifies the
content-addressed dataset before returning cases or the scoring rubric. It also
exposes the separately recorded freeze identity used by later experiment phases.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.integrity import verify_manifest
from app.evaluation.dataset.loader import load_cases, load_rubric
from app.evaluation.dataset.models import EvaluationCase, ScoringRubric


class EvaluationDataset:
    """Provides access to the repository's frozen Phase 5 release.

    Args:
        repository_root: Repository containing the versioned dataset and freeze
            manifest.

    Attributes:
        root: Path to the Phase 5 v1 dataset release.
        freeze_path: Path to the Phase 5 freeze manifest.
    """

    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root / "data" / "evaluation" / "phase5" / "v1"
        self.freeze_path = repository_root / "docs" / "phase-5-freeze-manifest.json"

    def verify(self) -> None:
        """Verifies the dataset's membership, hashes, counts, and contracts.

        Raises:
            OSError: If a required release artifact cannot be read.
            ValueError: If the release differs from its content manifest or an
                artifact violates its schema.
        """
        verify_manifest(self.root)

    def cases(self, split: DatasetSplit) -> list[EvaluationCase]:
        """Loads verified evaluation cases for one dataset split.

        Args:
            split: Dataset partition to select.

        Returns:
            Cases in their declared release order, restricted to ``split``.

        Raises:
            OSError: If a required release artifact cannot be read.
            ValueError: If dataset integrity or case validation fails.
        """
        self.verify()
        return [case for case in load_cases(self.root / "cases.jsonl") if case.split == split]

    def rubric(self) -> ScoringRubric:
        """Loads the verified scoring rubric.

        Returns:
            The versioned scoring and statistical protocol.

        Raises:
            OSError: If a required release artifact cannot be read.
            ValueError: If dataset integrity or rubric validation fails.
        """
        self.verify()
        return load_rubric(self.root / "scoring-rubric.json")

    def freeze_identity(self) -> dict[str, object]:
        """Loads the aggregate identity of the frozen Phase 5 release.

        Returns:
            The freeze manifest as a JSON object.

        Raises:
            OSError: If the freeze manifest cannot be read.
            json.JSONDecodeError: If the freeze manifest is not valid JSON.
            ValueError: If the decoded manifest is not a JSON object.
        """
        value: object = json.loads(self.freeze_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Phase 5 freeze manifest must be an object")
        return value
