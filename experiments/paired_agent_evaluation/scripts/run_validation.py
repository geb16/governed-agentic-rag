"""Acquires a named Phase 6 validation run for harness calibration.

The command executes the validation split before the preregistered test run is
claimed. Use a new run ID when calibration changes require another acquisition;
an existing run ID resumes only when its attempt journals permit it.

Usage:
    python run_validation.py --run-id run_2025w06_validation
"""

from __future__ import annotations

import argparse

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.composition import acquire


def main() -> int:
    """Parses the run ID, acquires validation observations, and prints the manifest."""

    parser = argparse.ArgumentParser(description="Acquire the Phase-6 validation split.")
    parser.add_argument("--run-id", required=True, help="Identity matching ^run_[A-Za-z0-9_-]+$")
    args = parser.parse_args()
    manifest = acquire(run_id=args.run_id, split=DatasetSplit.VALIDATION)
    print(manifest.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
