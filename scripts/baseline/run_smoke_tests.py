"""Run the deterministic Phase 3 smoke suite and propagate pytest's exit status.

Covers FastAPI startup, health probes, authenticated invocation, one grounded
agent turn, and the frozen tool registry, using lexical retrieval, isolated
SQLite state, and model doubles; no provider or Qdrant is contacted. Pytest
runs with strict config and markers and without its cache provider.
Core:
    - SMOKE_TARGETS: pytest node IDs forming the smoke suite.
    - main: runs the suite in a subprocess and returns its exit code.
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
