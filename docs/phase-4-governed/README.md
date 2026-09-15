# Phase 4 governed treatment

## 1. Purpose and status

Phase 4 is the governed treatment evaluated against the frozen `phase3-baseline-v2` control. It
adds explicit classification, risk assessment, approval routing, bounded recovery, durable workflow
state, and tamper-evident audit events without changing the Phase 3 code or manifest.

The treatment is a synthetic research pilot. It is designed to measure reliability, safety,
traceability, and groundedness under controlled tasks; passing its engineering checks does not by
itself establish that governance improves those outcomes.

The control contract is documented in [Phase 3 baseline](../phase-3-baseline/README.md). Phase 4 component
ownership, trust boundaries, failure behavior, and architectural compromises are documented in
[Phase 4 governance architecture](architecture/phase4_governance_architecture.md).

## 2. Runtime configuration

The governed application uses the shared `RAG_` settings plus these Phase 4 settings:

```dotenv
RAG_GOVERNANCE_APPROVAL_PRINCIPAL_ID=review-service-account
RAG_GOVERNANCE_APPROVAL_ROLES=finance_manager,fraud_reviewer,iam_administrator
RAG_GOVERNANCE_AUDIT_INTEGRITY_KEY=<independent-secret-of-at-least-32-characters>
```

`RAG_API_KEY` authenticates the configured pilot principal. Caller JSON cannot supply or override
that identity or its roles. Production requires the API key, at least one approval role, and the
independent audit-integrity key. Experiment runs also require the audit-integrity key. Development
and test may use a purpose-derived audit key so local deterministic tests remain self-contained.

Start the governed application with:

```bash
uv run uvicorn app.governed_main:app --host 127.0.0.1 --port 8000
```

Production disables the OpenAPI schema, Swagger UI, and ReDoc. Liveness remains independent of
model readiness; readiness returns unavailable until the governed workflow is composed.

`request_id` is the governed invocation idempotency key. Replaying identical request content
returns the existing workflow without repeating model or tool work. Reusing the identifier with
different content returns HTTP 409 Conflict.

## 3. Verification

Run the deterministic repository gate before review:

```bash
uv run pytest
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
uv run pyright
git diff --check
uv run python scripts/run_smoke_tests.py
uv run python scripts/verify_phase3_freeze.py
```

The Phase 3 verifier hashes frozen files byte-for-byte. On Windows, `uv.lock` must retain the LF
bytes recorded by the v2 manifest; automatic CRLF checkout conversion can otherwise report a
content change even when Git considers the file logically unchanged.

Run the provider-backed Phase 4 smoke check separately:

```bash
uv run python scripts/governance/run_smoke_tests.py
```

This command requires `RAG_OPENAI_API_KEY`, can make multiple provider requests, and can incur
usage. It runs one in-process HTTP workflow with lexical retrieval and an ephemeral SQLite database.
The test profile prevents writes to configured business state and prevents experiment-manifest
creation. Deterministic workflow behavior remains the responsibility of `tests/governance`.

## 4. Reproducibility boundary

Experiment-profile startup records a governed manifest only after the Phase 3 control manifest and
every file it names pass verification. The governed manifest records the baseline identity,
governance source digest, policy and schema versions, shared knowledge and tool identities, model
configuration, selected package versions, and a canonical configuration digest. Reusing a run
identifier with different configuration fails closed.

Phase 4 source, tests, and documentation remain outside the Phase 3 manifest. Frozen Phase 3 files
must not be changed to simplify Phase 4 implementation; deliberate baseline corrections require a
new reviewed baseline release.
