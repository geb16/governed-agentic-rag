"""Build the exact SHA-256-seeded paired schedule frozen in Phase-5 governed workflow."""

from __future__ import annotations

import hashlib

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.executions import Condition, ExecutionKey, ScheduledExecution


def condition_order(case_id: str, repetition: int, *, seed: int) -> tuple[Condition, Condition]:
    digest = hashlib.sha256(f"{seed}:{case_id}".encode()).digest()
    initial = (
        (Condition.BASELINE, Condition.GOVERNED)
        if digest[0] % 2 == 0
        else (Condition.GOVERNED, Condition.BASELINE)
    )
    return initial if repetition % 2 == 1 else (initial[1], initial[0])


def build_schedule(
    cases: list[EvaluationCase],
    *,
    repetitions: int,
    seed: int,
) -> list[ScheduledExecution]:
    schedule: list[ScheduledExecution] = []
    sequence = 1
    for case in sorted(cases, key=lambda item: item.case_id):
        for repetition in range(1, repetitions + 1):
            for pair_order, condition in enumerate(
                condition_order(case.case_id, repetition, seed=seed), start=1
            ):
                schedule.append(
                    ScheduledExecution(
                        sequence=sequence,
                        key=ExecutionKey(
                            case_id=case.case_id,
                            repetition=repetition,
                            condition=condition,
                        ),
                        split=case.split.value,
                        pair_order=pair_order,
                    )
                )
                sequence += 1
    return schedule
