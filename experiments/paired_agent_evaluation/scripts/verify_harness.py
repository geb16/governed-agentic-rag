from __future__ import annotations

import subprocess
import sys

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.composition import EvaluationPaths, load_experiment_config


def main() -> int:
    paths = EvaluationPaths.discover()
    failed_gates: list[str] = []
    for script in (
        "scripts/verify_phase3_freeze.py",
        "scripts/verify_phase4_freeze.py",
        "scripts/verify_phase5_freeze.py",
    ):
        result = subprocess.run(
            [sys.executable, script],
            cwd=paths.repository,
            check=False,
            text=True,
        )
        if result.returncode:
            failed_gates.append(script)
    dataset = Phase5Dataset(paths.repository)
    config = load_experiment_config(paths)
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
    if failed_gates:
        print(f"Evaluation harness blocked by {len(failed_gates)} inherited freeze gate(s).")
        return 1
    print("Evaluation harness and inherited freeze identities verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
