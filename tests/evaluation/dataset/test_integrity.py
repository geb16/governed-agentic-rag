# Ensure deterministic rendering and byte-level release integrity.

from pathlib import Path

from app.evaluation.dataset.generation.artifacts import check_artifacts
from app.evaluation.dataset.integrity import verify_manifest

DATA_ROOT = Path("data/evaluation/phase5/v1")


def test_release_matches_deterministic_generator() -> None:
    check_artifacts(DATA_ROOT)


def test_release_matches_content_manifest() -> None:
    verify_manifest(DATA_ROOT)
