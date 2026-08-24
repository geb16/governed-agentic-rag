"""Phase 3 HTTP-only response contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import Field

from app.domain.contracts import StrictModel


class HealthResponse(StrictModel):
    """Liveness or readiness status returned by baseline health endpoints."""

    service: str
    version: str
    status: Literal["ok", "ready", "not_ready"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
