"""Verifies or freezes the Phase 6 evaluation harness.

With no mode flag, the command checks readiness and inherited freeze identities.
``--write`` records the harness and completed validation run; ``--frozen``
rejects drift from that record. Readiness and filesystem errors produce a
nonzero exit status.

Usage:
    python verify_harness.py --frozen --harness-version VERSION
    python verify_harness.py --write --harness-version VERSION
        --release-version VERSION --validation-run-id ID --test-run-id ID
"""

from __future__ import annotations

import argparse
import sys

from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.experiment_control import (
    verify_harness_freeze,
    verify_harness_readiness,
    write_harness_freeze,
)


def main() -> int:
    """Runs the selected harness readiness, freeze, or verification mode."""

    parser = argparse.ArgumentParser(
        description="Verify readiness or freeze the Phase 6 harness before test acquisition."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true", help="Write the preregistered freeze")
    modes.add_argument("--frozen", action="store_true", help="Require and verify the freeze")
    parser.add_argument("--harness-version", type=int)
    parser.add_argument("--release-version")
    parser.add_argument("--validation-run-id")
    parser.add_argument("--test-run-id")
    args = parser.parse_args()
    if args.write and (
        not args.harness_version
        or not args.release_version
        or not args.validation_run_id
        or not args.test_run_id
    ):
        parser.error(
            "--write requires --harness-version, --release-version, "
            "--validation-run-id, and --test-run-id"
        )
    if args.frozen and not args.harness_version:
        parser.error("--frozen requires --harness-version")
    if not args.write and (args.release_version or args.validation_run_id or args.test_run_id):
        parser.error("release and run identifiers are accepted only with --write")
    if not (args.write or args.frozen) and args.harness_version:
        parser.error("--harness-version requires --write or --frozen")

    paths = EvaluationPaths.discover()
    try:
        if args.write:
            manifest = write_harness_freeze(
                paths,
                harness_version=int(args.harness_version),
                release_version=str(args.release_version),
                validation_run_id=str(args.validation_run_id),
                test_run_id=str(args.test_run_id),
            )
            print(f"Wrote {manifest.freeze_id}: {manifest.aggregate_sha256}")
        elif args.frozen:
            manifest = verify_harness_freeze(paths, harness_version=int(args.harness_version))
            print(f"Verified {manifest.freeze_id}: {manifest.aggregate_sha256}")
        else:
            verify_harness_readiness(paths)
            print("Evaluation harness readiness and inherited freeze identities verified.")
    except (OSError, ValueError) as error:
        print(f"Evaluation harness blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
