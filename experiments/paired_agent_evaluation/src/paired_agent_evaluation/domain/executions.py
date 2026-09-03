# Execution identities and the immutable paired schedule. 

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject undeclared fields in persisted experiment contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Condition(StrEnum):
    BASELINE = "baseline"
    GOVERNED = "governed"


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
