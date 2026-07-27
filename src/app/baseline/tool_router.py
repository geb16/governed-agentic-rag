from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.schemas import (
    RetrievedChunk,
    ToolCallRecord,
)


# ToolEXecution dataclass to hold the output of a tool execution, 
# the record of the tool call, and any retrieved chunks.
@dataclass(slots=True)
class ToolExecution:
    output_json: str
    record: ToolCallRecord
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
