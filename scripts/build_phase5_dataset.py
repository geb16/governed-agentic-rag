# Build or verify the deterministic Phase-5 dataset release.

from __future__ import annotations

import argparse
from pathlib import Path

from app.evaluation.dataset.generation.artifacts import check_artifacts, write_artifacts


def main() -> None:
    """Render the release, or verify it when --check is supplied."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path("data/evaluation/phase5/v1")
    if args.check:
        check_artifacts(root)
    else:
        write_artifacts(root)
        print(f"Rendered Phase-5 dataset at {root}")


if __name__ == "__main__":
    main()
