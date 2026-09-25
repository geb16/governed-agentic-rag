"""Persist deterministic, case-scoped tool-failure plans.

One plan per (case_id, tool_name) holds a remaining-failure budget; upserting
resets its consumed count. consume_fault decrements the budget and returns the
1-based attempt number, so injected failures are reproducible per case.
Core:
    - set_fault_plan: replaces a plan for an existing case (KeyError otherwise).
    - upsert_fault_plan: inserts or resets a plan in the current transaction.
    - consume_fault: claims the next planned failure, if any.
"""

from __future__ import annotations

import sqlite3

from app.domain.support import ConsumedFault, FaultPlan


def set_fault_plan(
    connection: sqlite3.Connection,
    case_id: str,
    plan: FaultPlan,
) -> None:
    """Replace a fault plan after validating its case partition."""

    case = connection.execute(
        "SELECT 1 FROM synthetic_cases WHERE case_id = ?",
        (case_id,),
    ).fetchone()
    if case is None:
        raise KeyError(f"Unknown synthetic case: {case_id}")
    upsert_fault_plan(connection, case_id, plan)


def upsert_fault_plan(
    connection: sqlite3.Connection,
    case_id: str,
    plan: FaultPlan,
) -> None:
    """Insert or reset one validated fault plan in the current transaction."""

    connection.execute(
        """
        INSERT INTO fault_plans(
            case_id, tool_name, mode, failures_remaining, failures_consumed, error_code
        ) VALUES (?, ?, ?, ?, 0, ?)
        ON CONFLICT(case_id, tool_name) DO UPDATE SET
            mode = excluded.mode,
            failures_remaining = excluded.failures_remaining,
            failures_consumed = 0,
            error_code = excluded.error_code
        """,
        (case_id, plan.tool_name, plan.mode.value, plan.failures, plan.error_code),
    )


def consume_fault(
    connection: sqlite3.Connection,
    case_id: str,
    tool_name: str,
) -> ConsumedFault | None:
    """Consume and number the next configured failure attempt, if available."""

    row = connection.execute(
        """
        SELECT mode, failures_remaining, failures_consumed, error_code
        FROM fault_plans WHERE case_id = ? AND tool_name = ?
        """,
        (case_id, tool_name),
    ).fetchone()
    if row is None or int(row["failures_remaining"]) <= 0:
        return None
    attempt_number = int(row["failures_consumed"]) + 1
    connection.execute(
        """
        UPDATE fault_plans
        SET failures_remaining = failures_remaining - 1,
            failures_consumed = failures_consumed + 1
        WHERE case_id = ? AND tool_name = ?
        """,
        (case_id, tool_name),
    )
    return ConsumedFault(
        mode=row["mode"],
        error_code=row["error_code"],
        attempt_number=attempt_number,
    )
