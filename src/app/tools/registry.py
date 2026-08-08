"""Single allowlisted capability registry shared by experimental conditions."""

from __future__ import annotations

from typing import Any

from app.domain.repositories import SyntheticRepository
from app.rag.retriever import Retriever
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
    """Build the exact dependency-injected tool set shared by both conditions.

    Args:
        retriever: Approved-knowledge retrieval boundary.
        repository: Isolated synthetic support-state boundary.

    Returns:
        Ordered controlled tools whose names form the model allowlist.
    """
    return [
        PolicyLookupTool(retriever),
        TicketLookupTool(repository),
        ResponseDrafterTool(),
        TicketUpdateTool(repository),
        IssueRefundTool(repository),
        ChangeAccessRoleTool(repository),
        HumanReviewTool(repository),
    ]
