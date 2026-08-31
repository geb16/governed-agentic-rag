"""Test deterministic rendering, strict manifests, and closed release membership."""

import json
import shutil
from pathlib import Path

import pytest

from app.evaluation.dataset.generation.artifacts import check_artifacts
from app.evaluation.dataset.integrity import verify_manifest

DATA_ROOT = Path("data/evaluation/phase5/v1")


def test_release_matches_deterministic_generator() -> None:
    """Keep checked-in artifacts byte-identical to deterministic rendering."""
    check_artifacts(DATA_ROOT)


def test_release_matches_content_manifest() -> None:
    """Verify the checked-in release against its closed content manifest."""
    verify_manifest(DATA_ROOT)


def _copy_release(destination: Path) -> Path:
    """Copy the release so negative tests cannot mutate source artifacts.

    Args:
        destination: Temporary parent directory.

    Returns:
        Path to the isolated release copy.
    """
    root = destination / "v1"
    shutil.copytree(DATA_ROOT, root)
    return root


def _mutate_manifest(root: Path, mutation: str, value: object = None) -> None:
    """Apply one structural or identity mutation to a copied manifest.

    Args:
        root: Isolated release directory.
        mutation: Field to replace, or ``remove`` to delete a field.
        value: Replacement value or field name to remove.
    """
    path = root / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "remove":
        payload.pop(str(value))
    else:
        payload[mutation] = value
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_integrity_and_generation_reject_an_unexpected_release_file(tmp_path: Path) -> None:
    """Prevent undeclared content from accompanying hashed artifacts.

    Args:
        tmp_path: Pytest-managed isolation directory.
    """
    root = _copy_release(tmp_path)
    (root / "notes.txt").write_text("undeclared\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"unexpected notes\.txt"):
        verify_manifest(root)
    with pytest.raises(ValueError, match=r"unexpected notes\.txt"):
        check_artifacts(root)


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("remove", "case_count"),
        ("unexpected_field", True),
        ("case_count", 99),
        ("validation_case_count", 19),
        ("baseline_freeze_id", "phase3-substituted"),
        ("governance_aggregate_sha256", "0" * 64),
    ],
)
def test_integrity_rejects_manifest_schema_count_and_parent_drift(
    tmp_path: Path,
    mutation: str,
    value: object,
) -> None:
    """Reject manifest schema, count, and parent-identity drift.

    Args:
        tmp_path: Pytest-managed isolation directory.
        mutation: Manifest field operation under test.
        value: Mutation-specific field name or replacement value.
    """
    root = _copy_release(tmp_path)
    _mutate_manifest(root, mutation, value)

    with pytest.raises(ValueError):
        verify_manifest(root)


def test_integrity_rejects_invalid_artifact_hash_format(tmp_path: Path) -> None:
    """Reject a noncanonical digest before content verification.

    Args:
        tmp_path: Pytest-managed isolation directory.
    """
    root = _copy_release(tmp_path)
    path = root / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["files"]["cases.jsonl"] = "not-a-sha256"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        verify_manifest(root)
