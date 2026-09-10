"""Seals a Phase 6 test run or verifies an existing release.

``--seal-run`` copies sanitized primary artifacts into the content-addressed
release root and records their aggregate SHA-256. Without that option, the
command verifies the existing release manifest and reports artifact drift.

Usage:
    python verify_release.py [--seal-run RUN_ID]
"""

from __future__ import annotations

import argparse

from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.release import seal_run, verify_release


def main() -> int:
    """Seals the selected run or verifies the existing release."""

    parser = argparse.ArgumentParser(description="Seal or verify the Phase 6 v1 release.")
    parser.add_argument("--seal-run")
    args = parser.parse_args()
    paths = EvaluationPaths.discover()
    manifest = (
        seal_run(run_root=paths.run_root(args.seal_run), release_root=paths.release)
        if args.seal_run
        else verify_release(paths.release)
    )
    print(f"Verified {manifest.release_id}: {manifest.aggregate_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
