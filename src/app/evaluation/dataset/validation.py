# Cross-case and frozen-tool validation for the Phase 5 benchmark. 

from __future__ import annotations

from pydantic import BaseModel

from app.evaluation.dataset.enums import DatasetSplit, ScenarioCategory
from app.tools.access_role import ChangeAccessRoleArguments
from app.tools.human_review import HumanReviewArguments
from app.tools.policy_lookup import PolicyLookupArguments
from app.tools.refund import IssueRefundArguments
from app.tools.response_drafter import ResponseDrafterArguments
from app.tools.ticket_lookup import TicketLookupArguments
from app.tools.ticket_update import TicketUpdateArguments

EXPECTED_CASE_COUNT = 100
EXPECTED_SPLITS = {DatasetSplit.VALIDATION: 20, DatasetSplit.TEST: 80}
EXPECTED_CATEGORIES = {
    ScenarioCategory.NORMAL: 17,
    ScenarioCategory.AMBIGUOUS: 16,
    ScenarioCategory.POLICY_SENSITIVE: 17,
    ScenarioCategory.HIGH_RISK: 17,
    ScenarioCategory.MISSING_INFORMATION: 16,
    ScenarioCategory.TOOL_FAILURE: 17,
}

_TOOL_INPUTS: dict[str, type[BaseModel]] = {
    "policy_lookup": PolicyLookupArguments,
    "ticket_lookup": TicketLookupArguments,
    "response_drafter": ResponseDrafterArguments,
    "update_ticket_status": TicketUpdateArguments,
    "issue_refund": IssueRefundArguments,
    "change_access_role": ChangeAccessRoleArguments,
    "request_human_review": HumanReviewArguments,
}

