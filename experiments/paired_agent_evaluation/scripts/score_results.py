from __future__ import annotations

import argparse

from paired_agent_evaluation.reporting import grade_ragas, score_run


# script to run score results and summarize the results 
# with optional secondary Ragas faithfulness grading
def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and score a Phase-6 run.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ragas", action="store_true", help="Run secondary Ragas faithfulness.")
    args = parser.parse_args()
    summary = score_run(run_id=args.run_id)
    if args.ragas:
        grades = grade_ragas(run_id=args.run_id)
        summary["secondary_ragas_grades"] = len(grades)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
