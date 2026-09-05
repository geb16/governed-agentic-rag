from __future__ import annotations

import subprocess
import sys

from paired_agent_evaluation.composition import EvaluationPaths


def main() -> int:
    paths = EvaluationPaths.discover()
    failed_gates: list[str] = []
    for script in (
        "scripts/verify_phase3_freeze.py",
        "scripts/verify_phase4_freeze.py",
        "scripts/verify_phase5_freeze.py",
    ):
        result = subprocess.run(
            [sys.executable, script],
            cwd=paths.repository,
            check=False,
            text=True,
        )
        if result.returncode:
            failed_gates.append(script)
   
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
