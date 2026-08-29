# Validate source traceability and the no-real-data boundary.

import json
from pathlib import Path
from typing import Any

from app.evaluation.dataset import EvaluationCase

DATA_ROOT = Path("data/evaluation/phase5/v1")

# Validating all design sources referenced by cases are present in the known sources list.
def test_all_design_sources_resolve(cases: list[EvaluationCase]) -> None:
    payload: Any = json.loads((DATA_ROOT / "sources.json").read_text(encoding="utf-8"))
    known = {item["source_id"] for item in payload["sources"]}
    assert known
    assert {source for case in cases for source in case.design_source_ids} <= known

