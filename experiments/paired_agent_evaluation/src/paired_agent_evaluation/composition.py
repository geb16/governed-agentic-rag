# Composition root for the independently versioned Phase-6 harness.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvaluationPaths:
    repository: Path
    project: Path
    artifacts: Path
    release: Path
    configs: Path

    @classmethod
    def discover(cls) -> EvaluationPaths:
        repository = Path(__file__).resolve().parents[4]
        project = repository / "experiments" / "paired_agent_evaluation"
        return cls(
            repository=repository,
            project=project,
            artifacts=repository / "artifacts" / "paired_agent_evaluation",
            release=repository / "data" / "evaluation" / "paired_agent_evaluation" / "v1",
            configs=project / "config",
        )

    def run_root(self, run_id: str) -> Path:
        validate_run_id(run_id)
        return self.artifacts / run_id


def validate_run_id(run_id: str) -> None:
    if re.fullmatch(r"run_[A-Za-z0-9_-]+", run_id) is None:
        raise ValueError("run_id must match run_[A-Za-z0-9_-]+")