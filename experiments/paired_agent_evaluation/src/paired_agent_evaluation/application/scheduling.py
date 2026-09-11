"""Build a reproducible, order-balanced schedule for paired evaluation.

Each case receives a deterministic SHA-256-derived starting condition. Successive
repetitions reverse that order so both conditions occupy each pair position.

References:
    [1] NIST/SEMATECH, "Choosing a Sampling Scheme."
        https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc332.htm
"""

from __future__ import annotations

import hashlib

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.executions import Condition, ExecutionKey, ScheduledExecution


def condition_order(case_id: str, repetition: int, *, seed: int) -> tuple[Condition, Condition]:
    """Returns the deterministic, repetition-balanced condition order.

    The seed and case identity select the first repetition's order. Odd
    repetitions retain that order and even repetitions reverse it.

    Args:
        case_id: Stable evaluation-case identifier.
        repetition: One-based repetition number.
        seed: Experiment seed used for deterministic assignment.

    Returns:
        Baseline and governed conditions in their execution order.
    """
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
    """Builds paired executions in stable case and repetition order.

    Args:
        cases: Evaluation cases to schedule.
        repetitions: Number of paired repetitions per case.
        seed: Experiment seed forwarded to condition assignment.

    Returns:
        Sequentially numbered executions containing both conditions for every
        case and repetition.
    """
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
