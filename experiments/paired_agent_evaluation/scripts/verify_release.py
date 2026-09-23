"""Seal a Phase 6 test run or verify a versioned release.

The default action verifies canonical v2. ``--release-version`` selects another release.
Initial sealing remains restricted to preregistered v1; a later deterministic
correction must explicitly name both the source run and superseded version.

E.g., to seal the preregistered v1 run, verify v2, or seal a corrective v2 release:
    python verify_release.py
    python verify_release.py --release-version v2
    python verify_release.py --seal-run run_test_v1
    python verify_release.py --seal-corrective-run run_test_v1 --release-version v2
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.release import seal_corrective_release, seal_run, verify_release

INITIAL_RELEASE_VERSION = "v1"
CANONICAL_RELEASE_VERSION = "v2"
CORRECTION_ID = "baseline-safety-terminal-error-v1"
CORRECTION_SUMMARY = (
    "Project baseline safety blocks into terminal_error_code so end-to-end "
    "recovery success is scored symmetrically across conditions."
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
  verify_release.py
  verify_release.py --release-version v2
  verify_release.py --seal-run run_test_v1
  verify_release.py --seal-corrective-run run_test_v1 --release-version v2
""",
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--seal-run",
        metavar="RUN_ID",
        help="seal the preregistered test run as the immutable v1 release",
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
        help="release to verify or create (default: v1 for --seal-run; otherwise v2)",
    )
    parser.add_argument(
        "--supersedes-version",
        type=_release_version,
        default=INITIAL_RELEASE_VERSION,
        metavar="VERSION",
        help="prior release used by --seal-corrective-run (default: v1)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Seal the selected run or verify the requested release."""

    parser = build_parser()
    args = parser.parse_args(argv)
    paths = EvaluationPaths.discover()
    release_version = args.release_version or (
        INITIAL_RELEASE_VERSION if args.seal_run else CANONICAL_RELEASE_VERSION
    )
    release_root = paths.release_root(release_version)
    if args.seal_run:
        if release_version != INITIAL_RELEASE_VERSION:
            parser.error("--seal-run is reserved for the preregistered v1 release")
        if args.supersedes_version != INITIAL_RELEASE_VERSION:
            parser.error("--supersedes-version is valid only with --seal-corrective-run")
        manifest = seal_run(run_root=paths.run_root(args.seal_run), release_root=release_root)
    elif args.seal_corrective_run:
        if release_version == args.supersedes_version:
            parser.error("a corrective release must use a new version")
        manifest = seal_corrective_release(
            run_root=paths.run_root(args.seal_corrective_run),
            prior_release_root=paths.release_root(args.supersedes_version),
            release_root=release_root,
            release_id=f"paired-agent-evaluation-{release_version}",
            correction_id=CORRECTION_ID,
            correction_summary=CORRECTION_SUMMARY,
        )
    else:
        if args.supersedes_version != INITIAL_RELEASE_VERSION:
            parser.error("--supersedes-version is valid only with --seal-corrective-run")
        manifest = verify_release(release_root)
    print(f"Verified {manifest.release_id}: {manifest.aggregate_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
