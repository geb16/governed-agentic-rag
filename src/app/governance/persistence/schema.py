"""Declare the versioned SQLite schema for workflows and approvals.

The schema enforces unique request and trace identities, one approval per workflow
role, and foreign-key relationships to shared synthetic cases and workflows.
Runtime initialization separately rejects unsupported schema versions.
"""

from app.governance.version import WORKFLOW_SCHEMA_VERSION

GOVERNANCE_SCHEMA_VERSION = WORKFLOW_SCHEMA_VERSION

SCHEMA = """
CREATE TABLE IF NOT EXISTS governance_workflows (
    workflow_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL,
    trace_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    state_version INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES synthetic_cases(case_id)
);

CREATE INDEX IF NOT EXISTS idx_governance_workflow_status
ON governance_workflows(status, updated_at);

CREATE TABLE IF NOT EXISTS governance_approvals (
    approval_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    proposal_digest TEXT NOT NULL,
    actor_id TEXT,
    comment TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    decided_at TEXT,
    UNIQUE (workflow_id, role),
    FOREIGN KEY (workflow_id) REFERENCES governance_workflows(workflow_id)
);

CREATE INDEX IF NOT EXISTS idx_governance_approval_pending
ON governance_approvals(workflow_id, status);
"""
