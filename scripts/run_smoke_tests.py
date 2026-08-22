"""Run the focused deterministic smoke suite for the Phase 3 baseline.

The selected tests exercise FastAPI startup, liveness and readiness, authenticated
invocation, one complete grounded agent turn, and the frozen shared tool registry.
They use local lexical retrieval, isolated SQLite state, and deterministic model
doubles; no provider, Qdrant, or production business system is contacted.
"""

from __future__ import annotations

import subprocess
import sys

SMOKE_TARGETS = (
    "tests/baseline/integration/test_health.py",
    "tests/baseline/integration/test_api.py",
    (
        "tests/baseline/integration/test_agent.py::"
        "test_agent_invocation_returns_valid_grounded_output"
    ),
    "tests/shared/integration/test_tools.py::test_shared_tool_registry_is_the_frozen_capability_set",
)


def main() -> int:
    """Execute the focused smoke targets and return Pytest's process status."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *SMOKE_TARGETS,
            "-q",
            "--strict-config",
            "--strict-markers",
            "-p",
            "no:cacheprovider",
        ],
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
