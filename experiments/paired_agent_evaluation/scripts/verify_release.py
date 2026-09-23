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
from paired_agent_evaluation.release import seal_corrective_release, seal_run, verify_release


def main() -> int:
    """Seals the selected run or verifies the existing release."""

    parser = argparse.ArgumentParser(description="Seal or verify a versioned Phase 6 release.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--seal-run")
    actions.add_argument("--seal-corrective-run")
    parser.add_argument("--release-version", default="v1")
    parser.add_argument("--supersedes-version", default="v1")
    args = parser.parse_args()
    paths = EvaluationPaths.discover()
    release_root = paths.release_root(args.release_version)
    if args.seal_run:
        if args.release_version != "v1":
            parser.error("--seal-run is reserved for the preregistered v1 release")
        manifest = seal_run(run_root=paths.run_root(args.seal_run), release_root=release_root)
    elif args.seal_corrective_run:
        if args.release_version == args.supersedes_version:
            parser.error("a corrective release must use a new version")
        manifest = seal_corrective_release(
            run_root=paths.run_root(args.seal_corrective_run),
            prior_release_root=paths.release_root(args.supersedes_version),
            release_root=release_root,
            release_id=f"paired-agent-evaluation-{args.release_version}",
            correction_id="baseline-safety-terminal-error-v1",
            correction_summary=(
                "Project baseline safety blocks into terminal_error_code so end-to-end "
                "recovery success is scored symmetrically across conditions."
            ),
        )
    else:
        manifest = verify_release(release_root)
    print(f"Verified {manifest.release_id}: {manifest.aggregate_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
