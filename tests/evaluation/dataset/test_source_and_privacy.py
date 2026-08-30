# Validate source traceability and the no-real-data boundary.

import json
import re
from pathlib import Path
from typing import Any

from app.evaluation.dataset import EvaluationCase

DATA_ROOT = Path("data/evaluation/phase5/v1")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


# Validating all design sources referenced by cases are present in the known sources list.
def test_all_design_sources_resolve(cases: list[EvaluationCase]) -> None:
    payload: Any = json.loads((DATA_ROOT / "sources.json").read_text(encoding="utf-8"))
    known = {item["source_id"] for item in payload["sources"]}
    assert known
    assert {source for case in cases for source in case.design_source_ids} <= known


# Validating that all queries in the release contain no real-world identifiers.
def test_queries_contain_only_synthetic_identifiers(cases: list[EvaluationCase]) -> None:
    for case in cases:
        query = case.request.query
        assert not _EMAIL.search(query)
        assert not _IPV4.search(query)
        assert "social security" not in query.casefold()
        assert "national insurance" not in query.casefold()
