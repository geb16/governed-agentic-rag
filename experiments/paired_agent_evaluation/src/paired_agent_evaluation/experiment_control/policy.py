"""Declare stable experiment-control policy and identity derivation."""

RELEASE_PLACEHOLDERS = frozenset({"README.md"})
INHERITED_VERIFIERS = (
    "scripts/baseline/verify_freeze.py",
    "scripts/governance/verify_freeze.py",
    "scripts/evaluation/verify_freeze.py",
)


def harness_freeze_id(harness_version: int) -> str:
    """Return the freeze identity for a positive harness version."""
    if harness_version < 1:
        raise ValueError("harness version must be a positive integer")
    return f"paired-agent-evaluation-harness-v{harness_version}"
