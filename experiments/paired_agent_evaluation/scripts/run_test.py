"""Acquires the preregistered Phase 6 test split exactly once.

The command claims the fail-closed test-execution gate before invoking either
system. Run it only after validation and harness verification; subsequent test
acquisition attempts for the frozen harness are rejected.

Usage:
    python run_test.py --run-id run_2025w06_test
"""

from __future__ import annotations

import argparse

from paired_agent_evaluation.composition import acquire_preregistered_test


def main() -> int:
    """Claims the test-execution gate and acquires the test run."""

    parser = argparse.ArgumentParser(description="Acquire the untouched Phase 6 test split.")
    parser.add_argument("--run-id", required=True, help="Identity matching ^run_[A-Za-z0-9_-]+$")
    args = parser.parse_args()
    manifest = acquire_preregistered_test(run_id=args.run_id)
    print(manifest.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
