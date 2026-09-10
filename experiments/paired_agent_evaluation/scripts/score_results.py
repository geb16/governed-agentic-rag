"""Scores a Phase 6 run and writes its reporting artifacts.

The command normalizes observations, applies blinded adjudications, computes
paired and per-condition estimates, and updates the run manifest. Runs with
unresolved contributions remain awaiting adjudication. The optional ``--ragas``
flag also computes secondary faithfulness grades.

Usage:
    python score_results.py --run-id run_2025w06_test [--ragas]
"""

from __future__ import annotations

import argparse

from paired_agent_evaluation.reporting import grade_ragas, score_run


def main() -> int:
    """Generates primary reports and optional secondary Ragas grades."""

    parser = argparse.ArgumentParser(description="Normalize and score a Phase-6 run.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ragas", action="store_true", help="Run secondary Ragas faithfulness.")
    args = parser.parse_args()
    summary = score_run(run_id=args.run_id)
    if args.ragas:
        grades = grade_ragas(run_id=args.run_id)
        summary["secondary_ragas_grades"] = len(grades)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
