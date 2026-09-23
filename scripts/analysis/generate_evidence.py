"""Generate deterministic Phase 7 evidence from the sealed Phase 6 release."""

from __future__ import annotations

from pathlib import Path

from evidence.evidence_config import RELEASE_ID
from evidence.evidence_io import load_release
from evidence.evidence_tables import generate_tables
from figures.figure_conditions import render_condition_estimates
from figures.figure_overall import render_overall_effects


def main() -> int:
    # Verify sealed inputs and regenerate all derived Phase 7 evidence.

    script = Path(__file__).resolve()
    repository = script.parents[2]
    release = repository / "data/evaluation/paired_agent_evaluation/v1"
    output = repository / "docs/phase-7-analysis/generated"
    output.mkdir(parents=True, exist_ok=True)

    data = load_release(release)
    generate_tables(data, output)
    render_overall_effects(
        [row for row in data.differences if row["stratum"] == "overall"],
        output / "figure-1-overall-effects.svg",
    )
    render_condition_estimates(data.estimates, output / "figure-2-condition-estimates.svg")
    print(f"Generated Phase 7 evidence files from {RELEASE_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
