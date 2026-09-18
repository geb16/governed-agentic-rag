"""Strict identity contract for the versioned Phase 5 dataset release.

Pins the dataset's identity constants and binds its manifest to the exact
reviewed Phase 3 baseline and Phase 4 governance aggregate hashes, so a
substituted parent release fails validation instead of silently drifting.
Core:
    - DatasetManifest: closed file-set and SHA-256 schema with ancestry checks.
    - create_dataset_manifest(): builds the canonical manifest from file hashes.
References:
    [1] NIST, "Secure Hash Standard," FIPS 180-4, 2015. https://doi.org/10.6028/NIST.FIPS.180-4
    [2] SLSA, "Build: Provenance," v1.0, 2023. https://slsa.dev/spec/v1.0/provenance
"""

from __future__ import annotations

import re
from typing import Literal, Self

from pydantic import field_validator, model_validator

from app.evaluation.dataset.models import EvaluationModel

DATASET_ID = "enterprise-support-agent-eval"
DATASET_VERSION = "1.0.0"
DATASET_DISTRIBUTION_TYPE = "stratified_challenge_set_not_prevalence_sample"
DATASET_RELEASED_AT = "2026-09-17T00:00:00Z"
DATASET_CASE_COUNT = 100
DATASET_VALIDATION_CASE_COUNT = 20
DATASET_TEST_CASE_COUNT = 80
PHASE3_FREEZE_ID = "phase3-baseline-v5"
PHASE3_AGGREGATE_SHA256 = "84039d82823c5d85f72b383e80605c4187c0f02f1f9473cb569c1f69dcffbdc6"
PHASE4_FREEZE_ID = "phase4-governance-v6"
PHASE4_AGGREGATE_SHA256 = "a97c4c2b477a61ae340a43bf5c0bcbc3cc294ffc1dddf6a3bc2ea362486c2fc4"

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
    """Bind exact artifact bytes to the reviewed dataset and parent releases."""

    manifest_schema_version: Literal[1]
    dataset_id: Literal["enterprise-support-agent-eval"]
    dataset_version: Literal["1.0.0"]
    distribution_type: Literal["stratified_challenge_set_not_prevalence_sample"]
    released_at: Literal["2026-09-17T00:00:00Z"]
    case_count: Literal[100]
    validation_case_count: Literal[20]
    test_case_count: Literal[80]
    baseline_freeze_id: Literal["phase3-baseline-v5"]
    baseline_aggregate_sha256: str
    governance_freeze_id: Literal["phase4-governance-v6"]
    governance_aggregate_sha256: str
    files: dict[str, str]

    @field_validator(
        "baseline_aggregate_sha256",
        "governance_aggregate_sha256",
    )
    @classmethod
    def validate_parent_digest(cls, value: str) -> str:
        """Validate a parent-release digest.

        Args:
            value: Digest supplied by the manifest.

        Returns:
            The unchanged canonical digest.

        Raises:
            ValueError: If the value is not a lowercase SHA-256 digest.
        """
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("parent identity must be a lowercase SHA-256 digest")
        return value

    @field_validator("files")
    @classmethod
    def validate_file_map(cls, value: dict[str, str]) -> dict[str, str]:
        """Validate the closed artifact allowlist and its hashes.

        Args:
            value: Relative artifact names mapped to expected digests.

        Returns:
            The validated mapping unchanged.

        Raises:
            ValueError: If file membership or any digest is invalid.
        """
        expected = set(DATASET_ARTIFACT_NAMES)
        if set(value) != expected:
            missing = sorted(expected - set(value))
            unexpected = sorted(set(value) - expected)
            details = [*(f"missing {name}" for name in missing)]
            details.extend(f"unexpected {name}" for name in unexpected)
            raise ValueError("artifact file set is invalid: " + ", ".join(details))
        if any(_SHA256_PATTERN.fullmatch(digest) is None for digest in value.values()):
            raise ValueError("artifact hashes must be lowercase SHA-256 digests")
        return value

    @model_validator(mode="after")
    def validate_inherited_identities(self) -> Self:
        """Bind the dataset to the reviewed Phase 3 and Phase 4 releases.

        Returns:
            The validated manifest instance.

        Raises:
            ValueError: If either inherited aggregate differs from its frozen release.
        """
        if self.baseline_aggregate_sha256 != PHASE3_AGGREGATE_SHA256:
            raise ValueError("baseline aggregate does not match the Phase 3 release")
        if self.governance_aggregate_sha256 != PHASE4_AGGREGATE_SHA256:
            raise ValueError("governance aggregate does not match the Phase 4 release")
        return self


def create_dataset_manifest(file_hashes: dict[str, str]) -> DatasetManifest:
    """Create the canonical manifest for deterministic artifact hashes.

    Args:
        file_hashes: Exact release artifact names mapped to SHA-256 digests.

    Returns:
        Manifest pinned to the reviewed dataset and inherited releases.

    Raises:
        ValueError: If the artifact map violates the closed manifest contract.
    """
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
