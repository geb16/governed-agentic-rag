from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentRuntimePolicy:
    """Immutable limits needed by the use case, detached from environment config."""

    max_query_chars: int
    max_agent_turns: int
    max_tool_calls: int
    safety_identifier_secret: str
