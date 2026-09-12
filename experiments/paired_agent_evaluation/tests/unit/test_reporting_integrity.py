"""Verify scoring accepts only the schedule committed by the run manifest."""

from __future__ import annotations

import pytest
from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.adapters.storage.filesystem import sha256_json
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.reporting import _validate_schedule


def _serialized_schedule(answer_case: EvaluationCase) -> tuple[list[dict[str, object]], list[str]]:
    """Return a serialized schedule and its ordered observation identities."""
    schedule = build_schedule([answer_case], repetitions=1, seed=1)
    payload = [item.model_dump(mode="json") for item in schedule]
    return payload, [item.key.observation_id for item in schedule]


def test_scoring_rejects_schedule_drift(answer_case) -> None:
    """Reject schedule bytes that differ from the run-manifest commitment."""
    payload, observation_ids = _serialized_schedule(answer_case)
    expected_sha256 = sha256_json(payload)
    payload[0]["pair_order"] = 2 if payload[0]["pair_order"] == 1 else 1

    with pytest.raises(ValueError, match="schedule has changed"):
        _validate_schedule(
            payload,
            observation_ids,
            expected_sha256=expected_sha256,
            expected_observations=len(payload),
        )


def test_scoring_rejects_same_count_identity_substitution(answer_case) -> None:
    """Reject substituted observations even when their total count is unchanged."""
    payload, observation_ids = _serialized_schedule(answer_case)
    observation_ids[-1] = observation_ids[0]

    with pytest.raises(ValueError, match="identities do not match"):
        _validate_schedule(
            payload,
            observation_ids,
            expected_sha256=sha256_json(payload),
            expected_observations=len(payload),
        )
