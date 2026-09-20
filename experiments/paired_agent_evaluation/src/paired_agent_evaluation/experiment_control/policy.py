"""Declare immutable paths and identifiers for experiment controls."""

from pathlib import Path

HARNESS_FREEZE_ID = "paired-agent-evaluation-harness-v1"
HARNESS_MANIFEST = Path("docs/phase-6-experiments/harness-freeze-manifest.json")
TEST_EXECUTION_CLAIM = Path("data/evaluation/paired_agent_evaluation/test-execution-claim.json")
RELEASE_PLACEHOLDERS = frozenset({"README.md"})
INHERITED_VERIFIERS = (
    "scripts/baseline/verify_freeze.py",
    "scripts/governance/verify_freeze.py",
    "scripts/evaluation/verify_freeze.py",
)
