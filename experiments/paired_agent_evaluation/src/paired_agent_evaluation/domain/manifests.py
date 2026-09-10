"""Content-addressed run and sealed-release manifests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import Field

from paired_agent_evaluation.domain.executions import StrictModel

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ExperimentManifest(StrictModel):
    """Bind one acquisition run to its inputs, infrastructure, and outputs."""

    schema_version: Literal[2] = 2
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    split: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    phase3_freeze_id: str
    phase3_aggregate_sha256: Sha256
    phase4_freeze_id: str
    phase4_aggregate_sha256: Sha256
    phase5_freeze_id: str
    phase5_aggregate_sha256: Sha256
    model_identifier: str
    retrieval_backend: str
    qdrant_collection: str
    configuration_sha256: Sha256
    runtime_settings_sha256: Sha256
    tool_schema_sha256: Sha256
    qdrant_snapshot_sha256: Sha256
    qdrant_point_count: int = Field(ge=1)
    schedule_sha256: Sha256
    blinding_plan_sha256: Sha256
    expected_observations: int = Field(ge=1)
    accepted_observations: int = Field(default=0, ge=0)
    invalid_observations: int = Field(default=0, ge=0)
    package_versions: dict[str, str]


class ReleaseManifest(StrictModel):
    """Describe the content-addressed artifacts in one sealed test release."""

    schema_version: int = 1
    release_id: str
    run_id: str
    source_run_manifest_sha256: Sha256
    files: dict[str, Sha256]
    aggregate_sha256: Sha256
    sealed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HarnessFreezeManifest(StrictModel):
    """Bind one reviewed harness revision to validation evidence and one test run."""

    schema_version: Literal[1] = 1
    freeze_id: str = Field(pattern=r"^paired-agent-evaluation-harness-v[1-9][0-9]*$")
    preregistered_test_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    validation_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    validation_run_manifest_sha256: Sha256
    validation_summary_sha256: Sha256
    phase3_freeze_id: str
    phase3_aggregate_sha256: Sha256
    phase4_freeze_id: str
    phase4_aggregate_sha256: Sha256
    phase5_freeze_id: str
    phase5_aggregate_sha256: Sha256
    source_files: dict[str, Sha256]
    aggregate_sha256: Sha256


class TestExecutionClaim(StrictModel):
    """Record the irreversible local claim made before test-provider invocation."""

    schema_version: Literal[1] = 1
    test_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    harness_freeze_id: str
    harness_aggregate_sha256: Sha256
    validation_run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    claimed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
