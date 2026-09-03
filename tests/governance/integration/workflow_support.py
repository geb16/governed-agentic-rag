"""Focused builders for governed-workflow integration scenarios."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.governance.contracts import (
    ClassificationDraft,
    GovernedFinalDraft,
    ProposedActionDraft,
    ProposedActionKind,
    Sensitivity,
    TaskIntent,
    TaskType,
)
from tests.governance.support import ScriptedGovernanceModel


def refund_model(
    amount_minor: int,
    *,
    final_answer: str = "The governed refund workflow completed.",
) -> ScriptedGovernanceModel:
    """Build a deterministic model script for a state-changing refund request."""
    return ScriptedGovernanceModel(
        classifications=[
            ClassificationDraft(
                intent=TaskIntent.REFUND,
                task_type=TaskType.STATE_CHANGING,
                sensitivity=Sensitivity.MODERATE,
                confidence=0.95,
                summary="A refund action was requested.",
            )
        ],
        proposals=[
            ProposedActionDraft(
                kind=ProposedActionKind.TOOL,
                tool_name="issue_refund",
                arguments_json=json.dumps(
                    {
                        "ticket_id": "TKT-1003",
                        "amount_minor": amount_minor,
                        "currency": "GBP",
                        "idempotency_key": f"phase4-{amount_minor}-refund",
                    }
                ),
                confidence=0.95,
                rationale="The request and policy evidence support a candidate refund.",
            )
        ],
        finals=[GovernedFinalDraft(answer=final_answer, grounded=False)],
    )


def expire_approval_route(
    database_path: Path,
    workflow_id: str,
    *,
    when: datetime,
) -> None:
    """Set both persisted approval-expiry signals to the supplied instant."""
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT state_json FROM governance_workflows WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row["state_json"])
        assert payload["approval_route"] is not None
        payload["approval_route"]["expires_at"] = when.isoformat()
        connection.execute(
            "UPDATE governance_workflows SET state_json = ? WHERE workflow_id = ?",
            (json.dumps(payload), workflow_id),
        )
        connection.execute(
            "UPDATE governance_approvals SET expires_at = ? WHERE workflow_id = ?",
            (when.isoformat(), workflow_id),
        )
