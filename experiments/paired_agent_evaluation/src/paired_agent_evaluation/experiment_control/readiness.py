"""Verify inherited freezes and fixed schedule cardinality.

References:
    [1] Python Software Foundation, "subprocess — Subprocess management."
        https://docs.python.org/3/library/subprocess.html
    [2] NIST, "AI Risk Management Framework Core," Measure 2.1.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import ExperimentConfig
from paired_agent_evaluation.experiment_control.contracts import EvaluationControlPaths
from paired_agent_evaluation.experiment_control.policy import INHERITED_VERIFIERS


def _load_json(path: Path) -> Any:
    """Loads one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _run_inherited_freeze_verifiers(paths: EvaluationControlPaths) -> None:
    """Runs inherited phase verifiers and reports all failures together."""
    failed: list[str] = []
    for script in INHERITED_VERIFIERS:
        result = subprocess.run(
            [sys.executable, script],
            cwd=paths.repository,
            check=False,
            text=True,
        )
        if result.returncode:
            failed.append(script)
    if failed:
        raise ValueError(f"Inherited freeze verification failed: {', '.join(failed)}")


def _verify_schedule_contract(paths: EvaluationControlPaths) -> None:
    """Validates the frozen observation count for each controlled split."""
    dataset = EvaluationDataset(paths.repository)
    config = ExperimentConfig.model_validate(_load_json(paths.configs / "experiment.json"))
    expected = {DatasetSplit.VALIDATION: 120, DatasetSplit.TEST: 480}
    for split, count in expected.items():
        schedule = build_schedule(
            dataset.cases(split),
            repetitions=config.repetitions_per_case,
            seed=config.condition_order_seed,
        )
        if len(schedule) != count:
            raise ValueError(
                f"{split.value} schedule has {len(schedule)} entries; expected {count}"
            )


def verify_harness_readiness(paths: EvaluationControlPaths) -> None:
    """Verifies inherited freezes and schedule cardinality before acquisition."""
    _run_inherited_freeze_verifiers(paths)
    _verify_schedule_contract(paths)
