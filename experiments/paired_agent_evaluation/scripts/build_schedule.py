"""Builds a deterministic execution schedule for a dataset split.

The command expands each case into paired baseline and governed runs using
the repetition count and condition-order seed from the experiment config. It
writes the resulting JSON within ``artifacts/paired_agent_evaluation`` and
rejects output paths outside that artifact root.

Usage:
    python build_schedule.py --split validation [--output PATH]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.adapters.storage.filesystem import atomic_json
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.composition import EvaluationPaths, load_experiment_config


def main() -> int:
    """Parses CLI arguments, builds the schedule, and writes it as JSON."""

    parser = argparse.ArgumentParser(description="Build a frozen-protocol Phase 6 schedule.")
    parser.add_argument("--split", choices=[item.value for item in DatasetSplit], required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help="Repository-relative output below artifacts/paired_agent_evaluation.",
    )
    args = parser.parse_args()
    paths = EvaluationPaths.discover()
    config = load_experiment_config(paths)
    cases = EvaluationDataset(paths.repository).cases(DatasetSplit(args.split))
    schedule = build_schedule(
        cases,
        repetitions=config.repetitions_per_case,
        seed=config.condition_order_seed,
    )
    output = (
        (paths.repository / args.output).resolve()
        if args.output
        else paths.artifacts / "schedules" / f"{args.split}.json"
    )
    try:
        output.relative_to(paths.artifacts.resolve())
    except ValueError as error:
        raise ValueError(
            "Schedule output must remain inside the experiment artifact root"
        ) from error
    atomic_json(output, [item.model_dump(mode="json") for item in schedule])
    print(f"Wrote {len(schedule)} scheduled observations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
