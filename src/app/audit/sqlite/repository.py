from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.audit.hashing import canonical_digest
from app.audit.schemas import (
    AUDIT_SCHEMA_VERSION,
    AuditActorType,
    AuditEvent,
    AuditEventType,
    AuditStage,
    AuditTrace,
)
from app.audit.sqlite.connection import AuditConnectionFactory
from app.audit.sqlite.mapper import event_from_row
from app.audit.sqlite.schema import SCHEMA
from app.audit.sqlite.transaction import begin_immediate
from app.audit.verifier import verify_hash_chain


class SqliteAuditRepository:
    """Append-only, hash-chained audit events for governed workflows."""

    def __init__(self, database_path: Path, *, integrity_key: bytes | None = None) -> None:
        self._connections = AuditConnectionFactory(database_path)
        self._integrity_key = integrity_key

    def initialize(self) -> None:
        self._connections.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connections.connect() as connection:
            connection.executescript(SCHEMA)
            row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'governance_audit_schema_version'"
            ).fetchone()
            if row is not None and int(row["value"]) != AUDIT_SCHEMA_VERSION:
                raise RuntimeError("Unsupported governance audit schema version")
            connection.execute(
                "INSERT OR IGNORE INTO schema_metadata(key, value) VALUES (?, ?)",
                ("governance_audit_schema_version", str(AUDIT_SCHEMA_VERSION)),
            )

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
    ) -> AuditEvent:
        safe_details = details or {}
        occurred_at = datetime.now(UTC)
        input_digest = (
            canonical_digest(input_value, key=self._integrity_key)
            if input_value is not None
            else None
        )
        output_digest = (
            canonical_digest(output_value, key=self._integrity_key)
            if output_value is not None
            else None
        )
        with self._connections.connect() as connection:
            begin_immediate(connection)
            previous = connection.execute(
                """
                SELECT sequence_number, event_hash
                FROM governance_audit_events
                WHERE workflow_id = ?
                ORDER BY sequence_number DESC LIMIT 1
                """,
                (workflow_id,),
            ).fetchone()
            sequence = int(previous["sequence_number"]) + 1 if previous else 1
            previous_hash = str(previous["event_hash"]) if previous else None
            event_id = f"evt_{uuid4().hex}"
            event_hash = canonical_digest(
                self._hash_payload(
                    event_id=event_id,
                    workflow_id=workflow_id,
                    trace_id=trace_id,
                    sequence=sequence,
                    stage=stage,
                    event_type=event_type,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    input_digest=input_digest,
                    output_digest=output_digest,
                    details=safe_details,
                    previous_hash=previous_hash,
                    schema_version=AUDIT_SCHEMA_VERSION,
                ),
                key=self._integrity_key,
            )
            event = AuditEvent(
                event_id=event_id,
                workflow_id=workflow_id,
                trace_id=trace_id,
                sequence_number=sequence,
                stage=stage,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                occurred_at=occurred_at,
                input_digest=input_digest,
                output_digest=output_digest,
                details=safe_details,
                previous_event_hash=previous_hash,
                event_hash=event_hash,
                schema_version=AUDIT_SCHEMA_VERSION,
            )
            self._insert(connection, event)
        return event

    def _insert(self, connection: Any, event: AuditEvent) -> None:
        connection.execute(
            """
            INSERT INTO governance_audit_events(
                event_id, workflow_id, trace_id, sequence_number, stage,
                event_type, actor_type, actor_id, occurred_at, input_digest,
                output_digest, details_json, previous_event_hash, event_hash,
                schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.workflow_id,
                event.trace_id,
                event.sequence_number,
                event.stage.value,
                event.event_type.value,
                event.actor_type.value,
                event.actor_id,
                event.occurred_at.isoformat(),
                event.input_digest,
                event.output_digest,
                json.dumps(event.details, sort_keys=True, separators=(",", ":")),
                event.previous_event_hash,
                event.event_hash,
                event.schema_version,
            ),
        )

    def _hash_payload(
        self,
        *,
        workflow_id: str,
        trace_id: str,
        sequence: int,
        event_id: str,
        stage: AuditStage,
        event_type: AuditEventType,
        actor_type: AuditActorType,
        actor_id: str | None,
        occurred_at: datetime,
        input_digest: str | None,
        output_digest: str | None,
        details: dict[str, Any],
        previous_hash: str | None,
        schema_version: int,
    ) -> dict[str, Any]:
        return {
            "event_id": event_id,
            "workflow_id": workflow_id,
            "trace_id": trace_id,
            "sequence_number": sequence,
            "stage": stage.value,
            "event_type": event_type.value,
            "actor_type": actor_type.value,
            "actor_id": actor_id,
            "occurred_at": occurred_at.isoformat(),
            "input_digest": input_digest,
            "output_digest": output_digest,
            "details": details,
            "previous_event_hash": previous_hash,
            "schema_version": schema_version,
        }

    def list_events(self, workflow_id: str) -> list[AuditEvent]:
        with self._connections.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM governance_audit_events
                WHERE workflow_id = ? ORDER BY sequence_number
                """,
                (workflow_id,),
            ).fetchall()
        return [event_from_row(row) for row in rows]

    def trace(self, workflow_id: str) -> AuditTrace:
        events = self.list_events(workflow_id)
        return AuditTrace(
            workflow_id=workflow_id,
            events=events,
            chain_valid=verify_hash_chain(events, key=self._integrity_key),
        )
