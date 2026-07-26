from enum import StrEnum

from pydantic import Field

from app.domain.schemas import StrictModel


class FailureMode(StrEnum):
    TRANSIENT_ERROR = "transient_error"
    TIMEOUT = "timeout"
    PERMANENT_ERROR = "permanent_error"


class AccessAccountRecord(StrictModel):
    subject_id: str = Field(pattern=r"^USR-[0-9]{4}$")
    role: str
    version: int = Field(ge=1)


class RefundRecord(StrictModel):
    refund_id: str
    ticket_id: str
    amount_minor: int = Field(gt=0)
    currency: str
    status: str
    idempotency_key: str