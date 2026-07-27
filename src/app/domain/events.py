from enum import StrEnum


class ExecutionEvent(StrEnum):
    """Names for basic logs only; Phase 3 deliberately has no audit-event pipeline."""

    REQUEST_RECEIVED = "baseline.request.received"
    INPUT_BLOCKED = "baseline.input.blocked"
    RETRIEVAL_COMPLETED = "baseline.retrieval.completed"
    MODEL_TURN_COMPLETED = "baseline.model_turn.completed"
    TOOL_EXECUTED = "baseline.tool.executed"
    OUTPUT_BLOCKED = "baseline.output.blocked"
    REQUEST_COMPLETED = "baseline.request.completed"
    REQUEST_FAILED = "baseline.request.failed"
