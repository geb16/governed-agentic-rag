"""Normalize heterogeneous frozen-system responses into common observations."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
    RawExecution,
)


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(
    raw: RawExecution,
    *,
    trace_facts: list[str] | None = None,
):
    if raw.acceptance == AcceptanceStatus.INVALID:
        return NormalizedObservation(
            key=raw.key,
            acceptance=raw.acceptance,
            latency_ms=raw.latency_ms,
            input_tokens=0,
            output_tokens=0,
            raw_sha256=_sha256_json(raw.model_dump(mode="json")),
        )