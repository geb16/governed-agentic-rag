"""Define HTTP-only response contracts for the baseline API.

Strict Pydantic models that live only at the transport edge and never leak
into the application layer.
Core:
    - HealthResponse: liveness/readiness status with a UTC timestamp.
References:
    [1] Pydantic, "Models." https://docs.pydantic.dev/latest/concepts/models/
"""

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
