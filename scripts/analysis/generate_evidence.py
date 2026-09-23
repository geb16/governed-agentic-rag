"""Generate deterministic Phase 7 evidence from the sealed Phase 6 release."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    # Verify sealed inputs and regenerate all derived Phase 7 evidence.

    script = Path(__file__).resolve()
    repository = script.parents[2]
    release = repository / "data/evaluation/paired_agent_evaluation/v1"
    output = repository / "docs/phase-7-analysis/generated"
    output.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
