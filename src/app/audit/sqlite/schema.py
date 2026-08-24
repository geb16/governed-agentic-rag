SCHEMA = """
CREATE TABLE IF NOT EXISTS governance_audit_events (
    event_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    stage TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    occurred_at TEXT NOT NULL,
    input_digest TEXT,
    output_digest TEXT,
    details_json TEXT NOT NULL,
    previous_event_hash TEXT,
    event_hash TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    UNIQUE (workflow_id, sequence_number),
    UNIQUE (workflow_id, event_hash),
    FOREIGN KEY (workflow_id) REFERENCES governance_workflows(workflow_id)
);

CREATE INDEX IF NOT EXISTS idx_governance_audit_workflow
ON governance_audit_events(workflow_id, sequence_number);

CREATE TRIGGER IF NOT EXISTS governance_audit_no_update
BEFORE UPDATE ON governance_audit_events
BEGIN
    SELECT RAISE(ABORT, 'governance audit events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS governance_audit_no_delete
BEFORE DELETE ON governance_audit_events
BEGIN
    SELECT RAISE(ABORT, 'governance audit events are append-only');
END;
"""
