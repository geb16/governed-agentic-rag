"""Define controlled filesystem locations for evaluation composition.

References:
    [1] OWASP, "Input Validation Cheat Sheet," allowlist validation.
        https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvaluationPaths:
    """Locates repository inputs and isolated evaluation artifact roots."""

    repository: Path
    project: Path
    artifacts: Path
    releases: Path
    harnesses: Path
    configs: Path

    @classmethod
    def discover(cls) -> EvaluationPaths:
        """Discovers evaluation paths relative to the installed package."""
        repository = Path(__file__).resolve().parents[5]
        project = repository / "experiments" / "paired_agent_evaluation"
        return cls(
            repository=repository,
            project=project,
            artifacts=repository / "artifacts" / "paired_agent_evaluation",
            releases=repository / "data" / "evaluation" / "paired_agent_evaluation",
            harnesses=repository / "docs" / "phase-6-experiments",
            configs=project / "config",
        )

    def run_root(self, run_id: str) -> Path:
        """Returns the artifact directory for a validated run identifier.

        Raises:
            ValueError: If the identifier could escape or alias the run namespace.
        """
        validate_run_id(run_id)
        return self.artifacts / run_id

    def release_root(self, version: str) -> Path:
        """Returns a validated versioned release directory."""
        if re.fullmatch(r"v[1-9][0-9]*", version) is None:
            raise ValueError("release version must match v[1-9][0-9]*")
        return self.releases / version

    def harness_manifest(self, harness_version: int) -> Path:
        """Return the manifest path for a positive harness version."""
        if harness_version < 1:
            raise ValueError("harness version must be a positive integer")
        return self.harnesses / f"harness-freeze-manifest-v{harness_version}.json"

    def test_claim(self, harness_version: int) -> Path:
        """Return the one-time claim path for a positive harness version."""
        if harness_version < 1:
            raise ValueError("harness version must be a positive integer")
        return self.releases / f"test-execution-claim-v{harness_version}.json"


def validate_run_id(run_id: str) -> None:
    """Validates a run identifier against the artifact-name allowlist.

    Raises:
        ValueError: If the identifier is malformed or contains path syntax.
    """
    if re.fullmatch(r"run_[A-Za-z0-9_-]+", run_id) is None:
        raise ValueError("run_id must match run_[A-Za-z0-9_-]+")
