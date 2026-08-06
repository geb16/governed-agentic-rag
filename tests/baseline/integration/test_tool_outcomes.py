import json

from app.baseline.tool_router import ToolRouter
from app.domain.schemas import ActionResultStatus, EvidenceType
from app.persistence.repository import SqliteSyntheticRepository
from app.tools.human_review import HumanReviewTool
from app.tools.refund import IssueRefundTool
from tests.support.baseline import tool_context


# Testing the simulated action and the human escalation share a neutral outcome contract, 
# - so that the baseline LLM can treat them interchangeably.
def test_simulated_action_and_escalation_share_neutral_outcome_contract(
    repository: SqliteSyntheticRepository,
) -> None:
    router = ToolRouter([IssueRefundTool(repository), HumanReviewTool(repository)])

    refund = router.execute(
        call_id="call_refund",
        name="issue_refund",
        arguments_json=(
            '{"ticket_id":"TKT-1003","amount_minor":75000,"currency":"GBP",'
            '"idempotency_key":"refund_case_default_001"}'
        ),
        context=tool_context(),
    )
    escalation = router.execute(
        call_id="call_escalate",
        name="request_human_review",
        arguments_json=(
            '{"ticket_id":"TKT-1001","reason":"Privileged role change requires human review.",'
            '"requested_role":"iam_manager","idempotency_key":"review_case_default_001"}'
        ),
        context=tool_context(),
    )
    repeated_refund = router.execute(
        call_id="call_refund_repeat",
        name="issue_refund",
        arguments_json=(
            '{"ticket_id":"TKT-1003","amount_minor":75000,"currency":"GBP",'
            '"idempotency_key":"refund_case_default_001"}'
        ),
        context=tool_context(),
    )

    assert refund.record.outcome.state_changed is True
    assert refund.record.outcome.simulated is True
    assert refund.record.evidence[0].evidence_type == EvidenceType.BUSINESS_RECORD
    assert escalation.record.proposal.action_type == "request_human_review"
    assert escalation.record.outcome.status == ActionResultStatus.EXECUTED
    assert json.loads(escalation.output_json)["status"] == "pending_human_review"
    assert repeated_refund.record.outcome.status == ActionResultStatus.NO_CHANGE
    assert (
        json.loads(repeated_refund.output_json)["refund_id"]
        == json.loads(refund.output_json)["refund_id"]
    )
