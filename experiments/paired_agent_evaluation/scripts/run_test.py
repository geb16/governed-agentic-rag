from __future__ import annotations

import argparse

from paired_agent_evaluation.composition import acquire_preregistered_test


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire the untouched Phase 6 test split.")
    parser.add_argument("--run-id", required=True, help="Identity matching ^run_[A-Za-z0-9_-]+$")
    args = parser.parse_args()
    manifest = acquire_preregistered_test(run_id=args.run_id)
    print(manifest.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
