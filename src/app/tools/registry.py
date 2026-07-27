from __future__ import annotations

from typing import Any

from app.rag.retriever import Retriever

from app.persistence.repository import SyntheticRepository
from app.tools.access_role import ChangeAccessRoleTool
from app.tools.base import ControlledTool
from app.tools.human_review import HumanReviewTool
from app.tools.policy_lookup import PolicyLookupTool
from app.tools.refund import IssueRefundTool
from app.tools.response_drafter import ResponseDrafterTool
from app.tools.ticket_lookup import TicketLookupTool
from app.tools.ticket_update import TicketUpdateTool


def build_shared_tools(
    retriever: Retriever,
    repository: SyntheticRepository,
) -> list[ControlledTool[Any]]:
    """
    Build the exact capability set shared by both experimental systems.
    """
    #  return a list of tool instances, each initialized with the appropriate dependencies
    return [
        PolicyLookupTool(retriever),
        TicketLookupTool(repository),
        ResponseDrafterTool(),
        TicketUpdateTool(repository),
        IssueRefundTool(repository),
        ChangeAccessRoleTool(repository),
        HumanReviewTool(repository),
    ]
