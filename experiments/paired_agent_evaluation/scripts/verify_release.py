"""Seal a Phase 6 test run or verify an explicitly selected release.

E.g., to seal v4, verify v4, or seal a corrective release:
    python verify_release.py --release-version v4
    python verify_release.py --seal-run run_test_v2 --release-version v4
    python verify_release.py --seal-corrective-run run_test_v1 --supersedes-version v2
        --release-version v3
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from paired_agent_evaluation.composition.paths import EvaluationPaths
from paired_agent_evaluation.release import seal_corrective_release, seal_run, verify_release

CORRECTION_ID = "baseline-human-review-route-v1"
CORRECTION_SUMMARY = (
    "Preserve a successful baseline human-review route when later final-answer "
    "citation validation records a terminal safety failure."
)


def _release_version(value: str) -> str:
    """Validate a release version for friendly command-line errors."""
    if not value.startswith("v") or not value[1:].isdigit() or value[1] == "0":
        raise argparse.ArgumentTypeError("must match v[1-9][0-9]* (for example, v1 or v2)")
    return value


def build_parser() -> argparse.ArgumentParser:
    """Build the release command-line parser."""
    parser = argparse.ArgumentParser(
        description="Seal or verify a versioned Phase 6 release.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  verify_release.py --release-version v4
  verify_release.py --seal-run run_test_v2 --release-version v4
  verify_release.py --seal-corrective-run run_test_v1 --supersedes-version v2 --release-version v3
""",
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--seal-run",
        metavar="RUN_ID",
        help="seal the preregistered test run as the selected release",
    )
    actions.add_argument(
        "--seal-corrective-run",
        metavar="RUN_ID",
        help="re-derive and seal a corrective release from an existing test run",
    )
    parser.add_argument(
        "--release-version",
        type=_release_version,
        metavar="VERSION",
        required=True,
        help="release to verify or create",
    )
    parser.add_argument(
        "--supersedes-version",
        type=_release_version,
        metavar="VERSION",
        help="prior release used by --seal-corrective-run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Seal the selected run or verify the requested release."""

    parser = build_parser()
    args = parser.parse_args(argv)
    paths = EvaluationPaths.discover()
    release_root = paths.release_root(args.release_version)
    if args.seal_run:
        if args.supersedes_version is not None:
            parser.error("--supersedes-version is valid only with --seal-corrective-run")
        manifest = seal_run(run_root=paths.run_root(args.seal_run), release_root=release_root)
    elif args.seal_corrective_run:
        if args.supersedes_version is None:
            parser.error("--seal-corrective-run requires --supersedes-version")
        if args.release_version == args.supersedes_version:
            parser.error("a corrective release must use a new version")
        manifest = seal_corrective_release(
            run_root=paths.run_root(args.seal_corrective_run),
            prior_release_root=paths.release_root(args.supersedes_version),
            release_root=release_root,
            release_id=f"paired-agent-evaluation-{args.release_version}",
            correction_id=CORRECTION_ID,
            correction_summary=CORRECTION_SUMMARY,
        )
    else:
        if args.supersedes_version is not None:
            parser.error("--supersedes-version is valid only with --seal-corrective-run")
        manifest = verify_release(release_root)
    print(f"Verified {manifest.release_id}: {manifest.aggregate_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
