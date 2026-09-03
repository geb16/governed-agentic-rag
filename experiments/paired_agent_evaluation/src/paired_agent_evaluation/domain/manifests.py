"""Content-addressed run and sealed-release manifests."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from paired_agent_evaluation.domain.executions import StrictModel


class ExperimentManifest(StrictModel):
    schema_version: int = 1
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    split: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    phase3_freeze_id: str
    phase3_aggregate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    phase4_freeze_id: str
    phase4_aggregate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    phase5_freeze_id: str
    phase5_aggregate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_identifier: str
    retrieval_backend: str
    qdrant_collection: str
    configuration_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    schedule_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_observations: int = Field(ge=1)
    accepted_observations: int = Field(default=0, ge=0)
    invalid_observations: int = Field(default=0, ge=0)
    package_versions: dict[str, str]


class ReleaseManifest(StrictModel):
    schema_version: int = 1
    release_id: str
    run_id: str
    source_run_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    files: dict[str, str]
    aggregate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sealed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
