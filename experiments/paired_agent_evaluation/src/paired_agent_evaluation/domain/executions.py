# Execution identities and the immutable paired schedule.

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject undeclared fields in persisted experiment contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Condition(StrEnum):
    BASELINE = "baseline"
    GOVERNED = "governed"


class AttemptState(StrEnum):
    """Describe the durable lifecycle of one acquisition attempt."""

    STARTED = "started"
    ACCEPTED = "accepted"
    PRE_ACCEPTANCE_FAILED = "pre_acceptance_failed"
    ACCEPTED_OBSERVATION_PERSISTED = "accepted_observation_persisted"
    INVALID_OBSERVATION_PERSISTED = "invalid_observation_persisted"


class ExecutionKey(StrictModel):
    case_id: str = Field(pattern=r"^case_eval_[0-9]{4}$")
    repetition: int = Field(ge=1, le=10)
    condition: Condition

    @property
    def observation_id(self) -> str:
        return f"{self.case_id}__r{self.repetition}__{self.condition.value}"


class ScheduledExecution(StrictModel):
    sequence: int = Field(ge=1)
    key: ExecutionKey
    split: str
    pair_order: int = Field(ge=1, le=2)


class AttemptRecord(StrictModel):
    """Persist acceptance evidence before an observation can be retried."""

    schema_version: int = 1
    observation_id: str
    attempt: int = Field(ge=1)
    state: AttemptState
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_type: str | None = None


class ExperimentConfig(StrictModel):
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
