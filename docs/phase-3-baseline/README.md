# Phase 3 baseline

## 1. Purpose and status

Phase 3 is the conventional agentic retrieval-augmented generation (RAG) control condition for
the later governed-agent comparison. Its freeze identifier is `phase3-baseline-v4`. The code uses
clean architecture (ports and adapters) with domain-owned contracts; it does not claim to be a
complete domain-driven design or a production governance platform.

The baseline is intentionally competent but governance-neutral. It provides bounded model and
tool execution, deterministic application security, synthetic state isolation, evidence tracking,
and reproducibility controls. Phase 4 can therefore measure governance workflow benefits without
being compared with an artificially unsafe or structurally weak control.

## 2. Documentation standard

Frozen Python modules follow the Google Python docstring conventions in [1]:

- every module states its responsibility;
- every public class, protocol, function, method, and property states its contract;
- non-obvious callables document `Args`, `Returns`, `Raises`, or `Note` sections when applicable;
- Pydantic models and enums use concise class docstrings because their typed fields are the
  authoritative schema;
- private helpers use docstrings only when their behavior is not clear from their name and types;
- docstrings describe guarantees, trust boundaries, side effects, and failure behavior rather
  than repeating implementation statements.

Type annotations remain the source of truth for types. Docstrings do not duplicate type syntax or
claim controls that the code does not enforce.

## 3. Architectural boundary

The architecture description follows the separation-of-concerns intent of [2]. This reference is
a design basis, not a formal claim of ISO/IEC/IEEE 42010 conformance.

| Layer | Responsibility | May depend on |
|---|---|---|
| `app.domain` | Strict task, evidence, action, model-turn, and synthetic support contracts | Python and Pydantic |
| `app.baseline.application` | Baseline contracts, use case, ports, invocation state, turn policy, and responses | Domain contracts |
| `app.baseline.api` | HTTP parsing, authentication dependency, health transport contract, and response transport | Baseline application boundary |
| `app.baseline.agent`, `app.baseline.tool_router` | Compatibility façade and allowlisted dispatch | Baseline application and domain contracts |
| `app.baseline.experiments` | Phase 3 run identity and immutable manifest recording | Baseline prompt, tool, configuration, and version contracts |
| `app.infrastructure` | OpenAI and SQLite adapters | Application ports and domain contracts |
| `app.rag`, `app.tools` | Retrieval, Qdrant, and controlled capability adapters | Domain ports and contracts |
| `app.baseline.composition`, `app.baseline_main` | Concrete Phase 3 wiring and process lifecycle | All outward adapters |

The dependency rule is enforced by `tests/baseline/architecture/test_baseline_boundaries.py`: the domain and
application layers cannot import outbound adapter packages. `app.baseline.composition.build_runtime`
is the Phase 3 composition root. `app.baseline.agent.BaselineAgent` remains a thin
constructor-compatible façade; orchestration belongs to `BaselineAgentService` and
`BaselineTurnRunner`.

### 3.1 Technology traceability

The implementation references only technologies present in `pyproject.toml` or the Python standard
library:

| Technology | Phase 3 use | Primary reference |
|---|---|---|
| FastAPI | HTTP routing, dependency injection, middleware, and application lifespan | [6] |
| Pydantic and Pydantic Settings | Strict boundary models, validation, JSON Schema, and configuration | [7] |
| OpenAI Python/Responses API | Structured model turns, function calls, embeddings, and safety identifier | [5], [10] |
| Qdrant Python client | Experiment-profile vector collection replacement and similarity queries | [8] |
| Python `sqlite3` | Transactional, case-partitioned synthetic support state | [9] |

SQLAlchemy and LangChain are deliberately not referenced: neither is declared as a dependency nor
imported by Phase 3. Persistence uses Python `sqlite3` directly, and agent orchestration is the
project's bounded application service rather than a framework-owned chain or graph.

## 4. Invocation sequence

One `POST /api/v1/baseline/invoke` request follows this sequence:

1. `create_app` loads validated settings, configures JSON logging, installs trusted-host and
   security middleware, and registers HTTP routers.
2. The application lifespan calls `build_runtime`, initializes the SQLite schema and default
   synthetic case, loads the approved knowledge corpus, and conditionally creates the model-backed
   agent. Experiment-profile composition also records and exposes the immutable run manifest before
   startup succeeds.
3. HTTP middleware performs an early declared-size check and adds defensive response headers.
   The authenticated route compares configured API keys in constant time.
4. Pydantic rejects undeclared fields and invalid request identifiers before the use case runs.
   `BaselineAgentService` then confirms the trusted `case_id` and applies deterministic input
   normalization and screening.
5. `KnowledgeRetriever` returns ranked chunks. Local Markdown must be named in `manifest.json`,
   remain inside the configured directory, satisfy the file-size bound, and match its SHA-256
   digest before chunking.
6. `build_user_prompt` serializes the request and retrieved knowledge as JSON explicitly labelled
   as untrusted data. System instructions remain a separate trusted model parameter.
7. `OpenAIResponsesModel` makes a non-persistent Responses API request with a keyed pseudonymous
   safety identifier, strict structured final output, strict tool schemas, one-call turns,
   provider timeout, retry, and output-token bounds. Strict schemas and disabling parallel calls
   follow the function-calling controls described in [5].
8. `BaselineTurnRunner` rejects mixed final/tool turns, multiple tool calls in one turn, excess
   tool calls, excess turns, and missing terminal output.
9. `ToolRouter` treats the model call as a proposal. It enforces the name allowlist, parses JSON,
   validates the selected Pydantic argument model, injects trusted case context, and returns a
   structured success, denial, or failure record.
10. `InvocationState` accumulates provider usage, controlled tool records, and only the evidence
    made available during that invocation. State is never shared between requests.
11. `OutputGuardrail` validates citation uniqueness and membership, grounded-answer citation
    presence, active content, secret-like output, and prompt-leakage patterns.
12. `BaselineResponseFactory` creates the terminal response. Operational logs record identifiers,
    status, timing, and counts; prompt bodies and durable governance audit events are excluded.

## 5. Controlled capability set

`build_shared_tools` is the single capability registry used by both experimental conditions.

| Tool | Effect |
|---|---|
| `policy_lookup` | Reads the approved synthetic knowledge corpus |
| `ticket_lookup` | Reads a ticket from the current synthetic case |
| `response_drafter` | Creates plain text but never sends a message |
| `update_ticket_status` | Changes only case-partitioned synthetic ticket state |
| `issue_refund` | Writes only to the synthetic refund ledger |
| `change_access_role` | Changes only a synthetic IAM account |
| `request_human_review` | Creates a pending synthetic review record, not an approval workflow |

All arguments are model-controlled and therefore untrusted. `ToolExecutionContext` is
application-controlled and supplies the case, request, and requester identifiers. Tools never
accept the case partition from model arguments. State-changing tools use idempotency or no-change
semantics where required, and every effect remains simulated.

## 6. Security model

The secure-development posture is informed by the NIST SSDF [3] and the OWASP AI Agent Security
Cheat Sheet [4]. These are engineering references, not certification claims.

| Threat or failure | Enforced control |
|---|---|
| Unauthorized HTTP access | Configured API key, constant-time comparison, production fail-closed validation |
| Identity disclosure to the model provider | Dedicated keyed pseudonymous safety identifier; raw requester identity is never sent |
| Host-header abuse | Explicit trusted-host middleware |
| Production API metadata exposure | OpenAPI schema and interactive documentation disabled in production |
| Oversized requests | Configured `Content-Length` rejection plus required deployment-proxy body limit |
| Direct or indirect prompt injection | Untrusted-data labelling, bounded deterministic input rules, strict tool boundary |
| Tool abuse or privilege escalation | Fixed allowlist, strict schemas, one call per turn, trusted case context |
| Cross-case state leakage | Every synthetic business row and operation is partitioned by `case_id` |
| Fabricated evidence | Per-invocation evidence allowlist and deterministic citation membership checks |
| Secret or active-content disclosure | Output patterns, secret-redacting logs, response hardening headers |
| Runaway execution or cost | Turn, tool-call, output-token, timeout, retry, retrieval, and document-size bounds |
| Irreversible external action | No external business-system writes; all action tools are simulated |

Prompt instructions are behavioral guidance, not authorization. Deterministic code owns identity,
bounds, schemas, allowlisting, case selection, execution, and final-output validation.

### 6.1 Residual risks and deployment obligations

- Prompt-injection detection is a defense-in-depth heuristic and cannot prove that text is safe.
- `Content-Length` is only an early application check. A reverse proxy or gateway must enforce the
  actual streamed-body limit, including omitted-length and chunked requests.
- Development and test may use the documented local safety-identifier fallback. Experiment and
  production profiles require an independent `RAG_SAFETY_IDENTIFIER_SECRET`; the inbound API key
  is never reused for provider pseudonymization.
- Retrieved documents and tool output remain untrusted even after integrity validation; a valid
  digest establishes identity, not truth or safety.
- SQLite and the supplied tools model synthetic evaluation state, not production availability,
  authorization, payments, IAM, or customer-data requirements.

## 7. Deliberate Phase 3 exclusions

Phase 3 contains no governance graph, formal risk classifier, policy decision engine, durable
approval, approval-bound action token, checkpoint/resume mechanism, compensating transaction,
or persistent audit-event pipeline. The model may choose `request_human_review`, but that record is
not proof of approval and does not authorize another action.

These exclusions define the experimental boundary. They must not be quietly added to the baseline
after freeze; they belong in the governed Phase 4 condition.

## 8. Reproducibility and freeze procedure

The experiment profile requires Qdrant, an OpenAI credential, a dedicated safety-identifier
secret, and a named run identifier.
`app.baseline.experiments.ExperimentRunManifest` records the freeze ID, models, knowledge digest,
prompt digest, strict tool schema digest, retrieval parameters, contract versions, selected package
versions, and a canonical configuration digest. Composition records this manifest automatically
before the experiment application becomes ready. A run identifier cannot be reused for different
configuration.

Before writing the freeze manifest:

1. review the source, docstrings, tests, knowledge manifest, dependency lock, and this baseline
   contract;
2. run Ruff formatting and linting, MyPy, Pyright, and the complete Pytest suite;
3. confirm the Git worktree contains only reviewed Phase 3 changes;
4. write `docs/phase-3-baseline/freeze-manifest.json` once with
   `uv run python scripts/baseline/verify_freeze.py --write`;
5. immediately verify it with `uv run python scripts/baseline/verify_freeze.py`;
6. review the generated file list and aggregate SHA-256 before committing and tagging.

The verifier freezes Phase-3 runtime code, normative architecture and baseline documents,
knowledge, dependencies, pinned Qdrant Compose configuration, ingestion and smoke scripts,
boundary tests, baseline tests, shared tests, and support fixtures.
`tests/governance` content is deliberately outside this identity. Any subsequent added,
removed, or modified frozen file must fail verification.

## 9. Verification evidence

The pre-freeze gate consists of:

- Ruff format check and lint over `src`, `tests`, and `scripts`;
- strict MyPy over `src`;
- Pyright over `src` and `tests`;
- the complete Pytest suite with cache generation disabled during final verification;
- `git diff --check`;
- freeze-scope tests confirming clean-architecture and Phase 3 contract coverage.

Passing these checks establishes that the reviewed implementation matches its executable contracts.
It does not establish Phase-4 governance effectiveness.

## References

[1] Google, “Google Python Style Guide,” sec. 3.8, *Google Open Source Style Guides*.
[Online]. Available: https://google.github.io/styleguide/pyguide.html. [Accessed: Jul. 27, 2026].

[2] *Software, Systems and Enterprise—Architecture Description*, ISO/IEC/IEEE Standard
42010:2022, Nov. 2022. [Online]. Available: https://www.iso.org/standard/74393.html.
[Accessed: Jul. 13, 2026].

[3] M. Souppaya, K. Scarfone, and D. Dodson, *Secure Software Development Framework (SSDF)
Version 1.1: Recommendations for Mitigating the Risk of Software Vulnerabilities*, NIST Special
Publication 800-218, Feb. 2022, doi: 10.6028/NIST.SP.800-218.

[4] OWASP Foundation, “AI Agent Security Cheat Sheet,” *OWASP Cheat Sheet Series*. [Online].
Available: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html.
[Accessed: Jun. 08, 2026].

[5] OpenAI, “Function calling,” *OpenAI API Documentation*. [Online]. Available:
https://developers.openai.com/api/docs/guides/function-calling. [Accessed: Jun. 21, 2026].

[6] S. Ramírez, “Lifespan Events,” *FastAPI Documentation*. [Online]. Available:
https://fastapi.tiangolo.com/advanced/events/. [Accessed: Jul. 13, 2026].

[7] Pydantic Services Inc., “Configuration,” *Pydantic Documentation*. [Online]. Available:
https://docs.pydantic.dev/latest/api/config/. [Accessed: Jul. 09, 2026].

[8] Qdrant Solutions GmbH, “Qdrant Python Client Documentation.” [Online]. Available:
https://python-client.qdrant.tech/. [Accessed: Jul. 02, 2026].

[9] Python Software Foundation, “`sqlite3`—DB-API 2.0 interface for SQLite databases,”
*Python Documentation*. [Online]. Available: https://docs.python.org/3/library/sqlite3.html.
[Accessed: Jul. 17, 2026].

[10] OpenAI, “Vector embeddings,” *OpenAI API Documentation*. [Online]. Available:
https://developers.openai.com/api/docs/guides/embeddings. [Accessed: Jun. 21, 2026].
