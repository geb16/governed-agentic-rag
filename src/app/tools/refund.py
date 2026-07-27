from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.schemas import (
    ControlledToolResult,
    StrictModel,
)


class IssueRefundArguments(StrictModel):
    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")
    amount_minor: int = Field(
        gt=0,
        le=5_000_000,
        description="Refund amount in the currency's minor unit, for example pence or cents.",
    )
    currency: Literal["GBP", "USD", "EUR"]
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,100}$")


class IssueRefundResult(ControlledToolResult):
    refund_id: str | None = None
    ticket_id: str
    amount_minor: int
    currency: str
    status: str

