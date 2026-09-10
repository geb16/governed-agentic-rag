"""Defines validated identities, schedules, and acquisition attempt states."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject undeclared fields in persisted experiment contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Condition(StrEnum):
    """Identifies the system condition assigned to an execution."""

    BASELINE = "baseline"
    GOVERNED = "governed"


class AttemptState(StrEnum):
    """Identifies the persisted lifecycle state of an acquisition attempt.

    ``started`` is intentionally indeterminate after interruption. Only a
    confirmed ``pre_acceptance_failed`` attempt is eligible for retry; accepted
    attempts must not be repeated, whether or not their observation was stored.
    """

    STARTED = "started"
    ACCEPTED = "accepted"
    PRE_ACCEPTANCE_FAILED = "pre_acceptance_failed"
    ACCEPTED_OBSERVATION_PERSISTED = "accepted_observation_persisted"
    INVALID_OBSERVATION_PERSISTED = "invalid_observation_persisted"


class ExecutionKey(StrictModel):
    """Uniquely identifies a case repetition under one condition."""

    case_id: str = Field(pattern=r"^case_eval_[0-9]{4}$")
    repetition: int = Field(ge=1, le=10)
    condition: Condition

    @property
    def observation_id(self) -> str:
        """Returns the stable filesystem-safe observation identity."""
        return f"{self.case_id}__r{self.repetition}__{self.condition.value}"


class ScheduledExecution(StrictModel):
    """Places an execution key in the deterministic paired schedule."""

    sequence: int = Field(ge=1)
    key: ExecutionKey
    split: str
    pair_order: int = Field(ge=1, le=2)


class AttemptRecord(StrictModel):
    """Records retry-relevant state and timestamps for one attempt."""

    schema_version: int = 1
    observation_id: str
    attempt: int = Field(ge=1)
    state: AttemptState
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_type: str | None = None


class ExperimentConfig(StrictModel):
    """Defines the frozen execution controls for a paired experiment."""

    schema_version: int = 1
    experiment_id: str
    dataset_version: str
    rubric_version: str
    conditions: list[Condition]
    repetitions_per_case: int = Field(ge=1, le=10)
    condition_order_seed: int
    max_pre_acceptance_attempts: int = Field(ge=1, le=3)
    execution_concurrency: int = Field(ge=1, le=1)
    required_execution_profile: str
    required_retrieval_backend: str
