# Phase 3 baseline

## 1. Purpose and status

Phase 3 is the conventional agentic retrieval-augmented generation (RAG) control condition for
the later governed-agent comparison. Its freeze identifier is `phase3-baseline-v1`. The code uses
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
| `app.domain` | Strict task, evidence, action, and synthetic support contracts | Python and Pydantic |
| `app.application.baseline` | Baseline use case, ports, invocation state, turn policy, and responses | Domain contracts |
| `app.baseline` | Compatibility façade, deterministic guardrails, and allowlisted dispatch | Application and domain contracts |
| `app.infrastructure` | Provider adapters, currently OpenAI Responses | Application ports and domain contracts |
| `app.persistence`, `app.rag`, `app.tools` | SQLite, retrieval, Qdrant, and controlled capability adapters | Domain ports and contracts |
| `app.api` | HTTP parsing, authentication dependency, and response transport | Application use-case port |
| `app.composition`, `app.main` | Concrete wiring and process lifecycle | All outward adapters |

The dependency rule is enforced by `tests/architecture/test_baseline_boundaries.py`: the domain and
application layers cannot import outbound adapter packages. `app.composition.build_runtime` is the
composition root. `app.baseline.agent.BaselineAgent` remains a thin constructor-compatible façade;
orchestration belongs to `BaselineAgentService` and `BaselineTurnRunner`.

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
   agent.
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
