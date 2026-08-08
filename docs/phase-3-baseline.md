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
