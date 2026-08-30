"""Strict identity contract for the versioned Phase 5 dataset release."""

from __future__ import annotations

import re

from app.evaluation.dataset.models import EvaluationModel

DATASET_ID = "enterprise-support-agent-eval"
DATASET_VERSION = "1.0.0"
DATASET_DISTRIBUTION_TYPE = "stratified_challenge_set_not_prevalence_sample"
DATASET_RELEASED_AT = "2026-08-25T00:00:00Z"
DATASET_CASE_COUNT = 100
DATASET_VALIDATION_CASE_COUNT = 20
DATASET_TEST_CASE_COUNT = 80
PHASE3_FREEZE_ID = "phase3-baseline-v2"
PHASE3_AGGREGATE_SHA256 = "cd8c823a477419f7010c6d5beae1069baa154496e79fe52ed7fcaefcfe05f4b0"
PHASE4_FREEZE_ID = "phase4-governance-v1"
PHASE4_AGGREGATE_SHA256 = "a06eb798830e3cefea72978acc22d79dd6a2c51e53cf204ededffd8e7ceec46b"

DATASET_ARTIFACT_NAMES = (
    "case.schema.json",
    "cases.jsonl",
    "rubric.schema.json",
    "scoring-rubric.json",
    "sources.json",
)
DATASET_RELEASE_NAMES = frozenset((*DATASET_ARTIFACT_NAMES, "manifest.json"))
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DatasetManifest(EvaluationModel):
    pass

def create_dataset_manifest(file_hashes: dict[str, str]) -> DatasetManifest:
    """Create the canonical manifest from deterministic artifact hashes."""
    return DatasetManifest(
        manifest_schema_version=1,
        dataset_id=DATASET_ID,
        dataset_version=DATASET_VERSION,
        distribution_type=DATASET_DISTRIBUTION_TYPE,
        released_at=DATASET_RELEASED_AT,
        case_count=DATASET_CASE_COUNT,
        validation_case_count=DATASET_VALIDATION_CASE_COUNT,
        test_case_count=DATASET_TEST_CASE_COUNT,
        baseline_freeze_id=PHASE3_FREEZE_ID,
        baseline_aggregate_sha256=PHASE3_AGGREGATE_SHA256,
        governance_freeze_id=PHASE4_FREEZE_ID,
        governance_aggregate_sha256=PHASE4_AGGREGATE_SHA256,
        files=file_hashes,
    )
