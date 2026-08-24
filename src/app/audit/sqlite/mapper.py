import json
import sqlite3

from app.audit.schemas import AuditEvent


def event_from_row(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        schema_version=int(row["schema_version"]),
        event_id=row["event_id"],
        workflow_id=row["workflow_id"],
        trace_id=row["trace_id"],
        sequence_number=int(row["sequence_number"]),
        stage=row["stage"],
        event_type=row["event_type"],
        actor_type=row["actor_type"],
        actor_id=row["actor_id"],
        occurred_at=row["occurred_at"],
        input_digest=row["input_digest"],
        output_digest=row["output_digest"],
        details=json.loads(row["details_json"]),
        previous_event_hash=row["previous_event_hash"],
        event_hash=row["event_hash"],
    )
