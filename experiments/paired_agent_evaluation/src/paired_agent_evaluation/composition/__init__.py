"""Expose the evaluation composition root through a stable public API.

References:
    [1] Alistair Cockburn, "Hexagonal Architecture."
        https://alistair.cockburn.us/hexagonal-architecture
"""

from paired_agent_evaluation.composition.acquisition import (
    acquire,
    acquire_preregistered_test,
)
from paired_agent_evaluation.composition.builder import prepare_run
from paired_agent_evaluation.composition.identity import load_experiment_config
from paired_agent_evaluation.composition.paths import EvaluationPaths

__all__ = [
    "EvaluationPaths",
    "acquire",
    "acquire_preregistered_test",
    "load_experiment_config",
    "prepare_run",
]
