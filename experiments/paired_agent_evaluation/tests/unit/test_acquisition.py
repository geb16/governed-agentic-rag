from datetime import UTC, datetime

from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)


class SequencedRunner:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, case, scheduled, workspace) -> RawExecution:
        self.calls += 1
        now = datetime.now(UTC)
        accepted = self.calls > 1
        return RawExecution(
            key=scheduled.key,
            acceptance=AcceptanceStatus.ACCEPTED if accepted else AcceptanceStatus.INVALID,
            request_accepted=accepted,
            started_at=now,
            completed_at=now,
            latency_ms=1,
            request={"query": case.request.query},
            state_before=BusinessState(),
            state_after=BusinessState(),
        )

