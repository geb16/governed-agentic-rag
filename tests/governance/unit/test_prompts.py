"""Regression checks for governance model responsibility boundaries."""

from app.governance.llm.prompts import CLASSIFICATION_PROMPT, PROPOSAL_PROMPT


def test_workflow_approval_is_not_modelled_as_missing_information() -> None:
    """Approval routing must be separated from request-completeness decisions."""

    assert "not workflow approval" in CLASSIFICATION_PROMPT
    assert "Never treat workflow approval as missing information" in PROPOSAL_PROMPT
