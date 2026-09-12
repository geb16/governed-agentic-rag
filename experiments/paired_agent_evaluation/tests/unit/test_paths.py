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
