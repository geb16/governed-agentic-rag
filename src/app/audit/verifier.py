from app.audit.hashing import canonical_digest
from app.audit.schemas import AuditEvent


def verify_hash_chain(events: list[AuditEvent], *, key: bytes | None = None) -> bool:
    """Verify sequence, identity consistency, linkage, and every event digest."""

    if not events:
        return False
    workflow_id = events[0].workflow_id
    trace_id = events[0].trace_id
    previous_hash: str | None = None
    for expected_sequence, event in enumerate(events, start=1):
        if (
            event.workflow_id != workflow_id
            or event.trace_id != trace_id
            or event.sequence_number != expected_sequence
            or event.previous_event_hash != previous_hash
        ):
            return False
        payload = {
            "event_id": event.event_id,
            "workflow_id": event.workflow_id,
            "trace_id": event.trace_id,
            "sequence_number": event.sequence_number,
            "stage": event.stage.value,
            "event_type": event.event_type.value,
            "actor_type": event.actor_type.value,
            "actor_id": event.actor_id,
            "occurred_at": event.occurred_at.isoformat(),
            "input_digest": event.input_digest,
            "output_digest": event.output_digest,
            "details": event.details,
            "previous_event_hash": event.previous_event_hash,
            "schema_version": event.schema_version,
        }
        if canonical_digest(payload, key=key) != event.event_hash:
            return False
        previous_hash = event.event_hash
    return True
