from typing import Any, Protocol

from app.audit.schemas import AuditActorType, AuditEvent, AuditEventType, AuditStage, AuditTrace


class AuditRepository(Protocol):
    """Append and verify governance events without exposing storage details."""

    def initialize(self) -> None: ...

    def append(
        self,
        *,
        workflow_id: str,
        trace_id: str,
        stage: AuditStage,
        event_type: AuditEventType,
        actor_type: AuditActorType,
        actor_id: str | None = None,
        input_value: Any | None = None,
        output_value: Any | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent: ...

    def list_events(self, workflow_id: str) -> list[AuditEvent]: ...

    def trace(self, workflow_id: str) -> AuditTrace: ...
