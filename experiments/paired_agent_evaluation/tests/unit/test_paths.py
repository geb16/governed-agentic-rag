"""Verify run paths remain within the configured artifact boundary."""

import pytest

from paired_agent_evaluation.composition import EvaluationPaths


@pytest.mark.parametrize(
    "run_id",
    ["../escape", "run/escape", "run_", "not-a-run"],
    ids=["parent-traversal", "nested-path", "missing-suffix", "missing-prefix"],
)
def test_run_identifier_cannot_escape_artifact_boundary(
    paths: EvaluationPaths,
    run_id: str,
) -> None:
    """Reject traversal, nested paths, and identifiers outside the run convention."""
    with pytest.raises(ValueError, match="run_id"):
        paths.run_root(run_id)


def test_valid_run_identifier_resolves_below_artifacts(paths: EvaluationPaths) -> None:
    """Resolve a valid run identifier as a direct child of artifacts."""
    assert paths.run_root("run_validation_001").parent == paths.artifacts


def test_control_versions_resolve_below_their_stable_roots(paths: EvaluationPaths) -> None:
    """Resolve CLI-selected controls without ambient generation state."""
    assert paths.release_root("v4") == paths.releases / "v4"
    assert paths.harness_manifest(2) == paths.harnesses / "harness-freeze-manifest-v2.json"
    assert paths.test_claim(2) == paths.releases / "test-execution-claim-v2.json"


@pytest.mark.parametrize("version", ["v0", "4", "v4/escape"])
def test_invalid_release_versions_are_rejected(paths: EvaluationPaths, version: str) -> None:
    """Reject malformed release selectors before filesystem access."""
    with pytest.raises(ValueError, match="release version"):
        paths.release_root(version)


@pytest.mark.parametrize("version", [0, -1])
def test_invalid_harness_versions_are_rejected(paths: EvaluationPaths, version: int) -> None:
    """Reject nonpositive harness selectors before filesystem access."""
    with pytest.raises(ValueError, match="harness version"):
        paths.harness_manifest(version)
