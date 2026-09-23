"""Generate deterministic Phase 7 evidence from the sealed Phase 6 release."""

from __future__ import annotations

from pathlib import Path

from evidence.evidence_io import load_release
from evidence.evidence_tables import generate_tables


def main() -> int:
    # Verify sealed inputs and regenerate all derived Phase 7 evidence.

    script = Path(__file__).resolve()
    repository = script.parents[2]
    release = repository / "data/evaluation/paired_agent_evaluation/v1"
    output = repository / "docs/phase-7-analysis/generated"
    output.mkdir(parents=True, exist_ok=True)

    data = load_release(release)
    generate_tables(data, output)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
