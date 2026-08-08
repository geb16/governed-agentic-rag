# Phase 3 baseline architecture

## Purpose and declared scope

This document describes the software architecture of the conventional Phase 3 agentic RAG
baseline identified as `phase3-baseline-v1`. It records the dependency direction, component
ownership, runtime flow, trust boundaries, extension seams, and known compromises that must be
reviewed before the baseline is frozen.

The design is clean architecture/ports-and-adapters with domain-owned contracts. It is intentionally
not a complete domain-driven design implementation: the pilot has a small support domain and does
not need aggregates, domain services, or repositories beyond demonstrated behavior.

In scope:

- authenticated FastAPI transport and health endpoints;
- a provider-neutral baseline invocation use case;
- bounded OpenAI Responses model turns;
- integrity-checked lexical or Qdrant retrieval;
- strict, allowlisted, simulated tools;
- case-partitioned synthetic SQLite state;
- deterministic input, tool, citation, and output controls;
- governance-neutral outcomes, evidence, operational logging, and an experiment-manifest utility.

Out of scope:

- production customer, payment, IAM, ticketing, or messaging side effects;
- formal risk classification, approval routing, or policy decisions;
- durable workflow state, checkpointing, compensation, or audit-event persistence;
- Phase 4 governed workflow implementation.

The detailed behavioral, security, reproducibility, and reference contract is maintained in
[Phase 3 baseline](phase-3-baseline.md).

## Layer and dependency model

Arrows below represent source-code dependency direction, not runtime control flow.

```text
                         main.py + composition.py
                        /          |             \
                       v           v              v
                 API transport  baseline       concrete adapters
                    app.api      façade       infrastructure / RAG
                       |        + guardrails    persistence / tools
                       |           |              |
                       +-----------+--------------+
                                   v
                         app.application.baseline
                      use case / ports / state / policy
                                   |
                                   v
                              app.domain
                    task / evidence / action / support

        app.core: cross-cutting configuration, logging, and HTTP security
```

The domain layer is the innermost boundary and imports no outer application package. The
application layer depends on domain contracts and selected cross-cutting `app.core` functions, not
on concrete model, retrieval, persistence, tool, or HTTP adapters. FastAPI routes depend on
`BaselineUseCase`, not `BaselineAgent` or concrete outbound adapters. `app.composition` is the only
composition root.

`app.baseline` is not an inner domain layer. It is a Phase 3 compatibility and policy-mechanism
package containing the constructor-compatible façade, deterministic guardrails, and tool router.

## Component ownership

| Component | Owns | Does not own |
|---|---|---|
| `app.api` | HTTP routes, dependency resolution, transport status | Agent orchestration or adapter construction |
| `BaselineUseCase` | Stable inbound invocation contract | FastAPI or provider details |
| `BaselineAgentService` | Case/input validation, retrieval coordination, terminal response selection | OpenAI SDK calls or tool implementation |
| `BaselineTurnRunner` | Turn/tool limits, model-turn validation, tool continuation, output decision | HTTP and persistent state construction |
| `InvocationState` | Per-request provider items, usage, citations, evidence, tool records | Cross-request or durable workflow state |
| `ModelGateway` / `OpenAIResponsesModel` | Model-port contract / OpenAI adapter | Tool authorization |
| `RetrievalGateway` / `KnowledgeRetriever` | Retrieval contract / lexical-Qdrant selection | Business-policy decisions |
| `ToolRouter` | Tool allowlist, JSON/schema validation, deterministic dispatch and outcomes | Model judgment or Phase 4 approval policy |
| `SyntheticRepository` / `SqliteSyntheticRepository` | Domain persistence contract / case-partitioned synthetic state | Production business-system state |
| `build_shared_tools` | Frozen intended capability set for experimental conditions | Risk classification or workflow routing |
| `build_runtime` | Concrete adapter construction and default synthetic-case initialization | Request-specific orchestration |
| `app.domain` | Strict task, evidence, action, result, and support-state language | Transport and provider representations |

## Startup sequence

1. `create_app` resolves validated settings, configures JSON logging, registers security middleware,
   trusted-host handling, health routes, and the baseline route.
2. FastAPI enters the application lifespan and calls `build_runtime`.
3. `KnowledgeRetriever` validates the knowledge manifest and loads deterministic chunks. The
   Qdrant profile also requires an existing ready collection.
4. `SqliteSyntheticRepository` creates or validates its schema and seeds the default synthetic case
   only when absent.
5. When an OpenAI credential is configured, the composition root creates the model adapter,
   shared tool registry, fault injector, router, and `BaselineAgent` façade. Otherwise, invocation
   remains unavailable while liveness can still succeed.
6. The lifespan publishes the assembled adapters through application state.

Startup fails rather than serving a partially initialized runtime when knowledge integrity,
database schema, or configured Qdrant readiness validation fails.

## Invocation and failure sequence

1. Trusted-host and security middleware apply declared-size checks and defensive response headers.
   API-key enforcement and Pydantic request validation occur at the HTTP boundary before the use
   case is invoked.
2. `BaselineAgentService` assigns a trace identifier and verifies that the supplied `case_id`
   identifies an existing synthetic partition.
3. `InputGuardrail` normalizes the query and applies deterministic size, control-character, and
   high-confidence attack-pattern checks.
4. `KnowledgeRetriever` obtains initial approved chunks through the configured lexical or Qdrant
   backend. `build_user_prompt` serializes request and retrieval content as untrusted JSON data.
5. `BaselineTurnRunner` calls `ModelGateway` with trusted instructions, strict tool schemas, a keyed
   pseudonymous safety identifier, and request-local conversation items.
6. Each model turn must contain either one tool proposal or one structured final draft. Mixed turns,
   parallel proposals, exhausted tool limits, and malformed terminal turns fail closed.
7. For a proposal, `ToolRouter` checks the allowlist, parses and validates arguments, injects trusted
   `ToolExecutionContext`, optionally consumes a deterministic fault, and executes only the selected
   simulated tool. The structured tool outcome is returned to the next bounded model turn.
8. For a final draft, `OutputGuardrail` validates citation uniqueness and membership, grounded-answer
   evidence, active content, secret-like output, and prompt leakage.
9. `BaselineResponseFactory` returns a completed, refused, or failed `BaselineResponse` with model,
   retrieval, usage, tool, evidence, safety, and trace metadata.

| Condition | Terminal behavior |
|---|---|
| Agent not configured | HTTP 503 before application invocation |
| Invalid HTTP schema | HTTP 422; use case is not invoked |
| Invalid supplied API key | HTTP 401; a missing production key is rejected during configuration |
| Unknown synthetic case | `failed` with `synthetic_case_not_found`; model is not invoked |
| Input safety rejection | `refused` with a stable safety category |
| Unknown or invalid tool proposal | Structured denied tool outcome; no tool executes |
| Injected or tool execution failure | Structured failed outcome with bounded retry semantics |
| Invalid model turn or output | `refused` or stable `failed` response without a success claim |
| Unexpected model/tool-loop exception | Secret-safe exception log and stable `failed` response |
| Unexpected validation or retrieval exception | Propagates to the transport error path; recorded as a compromise below |

## Security and data trust boundaries

| Data or actor | Trust classification | Enforcement boundary |
|---|---|---|
| HTTP caller, headers, and body | Untrusted | Trusted hosts, API key, declared-size check, Pydantic request schema |
| User query | Untrusted | Input normalization, guardrail, length bound, JSON data enclosure |
| Knowledge files | Allowlisted but content-untrusted | Directory confinement, file-size bound, manifest membership, SHA-256 identity |
| Retrieved chunks | Content-untrusted | Prompt separation and per-invocation evidence allowlist |
| Model output and tool arguments | Untrusted | Structured output, one-call turns, allowlist, strict Pydantic schemas |
| `ToolExecutionContext` | Trusted application data | Constructed from validated request context, never accepted from model arguments |
| Tool output | Content-untrusted | Structured result contracts, evidence capture, output guardrail |
| SQLite state | Trusted synthetic state | Foreign keys, transactions, idempotency, and `case_id` partitioning |
| API/OpenAI/Qdrant credentials | Secret configuration | `SecretStr`, HTTPS requirements, redacting logs, no response exposure |
| Operational logs | Internal diagnostics | Structured context, secret redaction, no prompt bodies; not a durable audit trail |

Model requests use `store=False`. Request conversation and evidence state live only for one
`invoke` call. Synthetic support state is intentionally durable on local storage. Experiment
manifests are durable when the recording utility is invoked; governance workflow state does not
exist in Phase 3.

The application-level `Content-Length` check is an early rejection only. The deployment gateway must
enforce the actual streamed-body limit, including omitted-length and chunked requests.

## Extension seams and Phase 4 boundary

- `BaselineUseCase` is the inbound seam a Phase 4 workflow may wrap without modifying the baseline.
- `ModelGateway`, `RetrievalGateway`, `ToolGateway`, safety policies, and repository protocols permit
  adapter replacement at composition time.
- `build_shared_tools` defines the intended common capability set. Phase 4 must reuse the frozen
  schemas and simulated effects for a valid paired comparison.
- Pydantic contracts provide explicit versionable integration boundaries.

Phase 4 may own risk classification, policy decisions, approval state, recovery, workflow
checkpoints, and structured audit events. Those concerns must compose outside the frozen
`BaselineUseCase`; inserting them into its turn loop would invalidate the control condition.

## Known architectural compromises

1. `ModelGateway` and `InvocationState` still expose provider-shaped `dict[str, Any]` conversation
   items, including `function_call_output`. The OpenAI SDK is isolated, but the application state is
   not fully provider-agnostic.
2. The application layer imports `app.core.logging` and `app.core.security` directly. These are
   stable cross-cutting functions, but dedicated logging and pseudonymization ports would create a
   stricter dependency inversion boundary.
3. `app.baseline` combines compatibility, deterministic safety, and tool dispatch. It is bounded by
   purpose but is not a pure clean-architecture layer.
4. `persistence/repository.py` and `baseline/tool_router.py` retain multiple related responsibilities
   and should be split only when change frequency or additional implementations justify it.
5. SQLite, lexical retrieval, and simulated tools are appropriate for the controlled pilot, not a
   claim of production throughput, distributed consistency, or external authorization.
6. Prompt-injection patterns and output rules are defense in depth, not proofs of semantic safety.
7. `ExperimentRunManifest` can create an immutable named-run artifact, but `build_runtime` and the
   FastAPI lifespan do not currently invoke it; `application.state.experiment_manifest` remains
   `None`. Automatic experiment recording must not be claimed until composition wires this utility.
8. `BaselineAgentService` converts exceptions raised by the model/tool turn runner into a stable
   failed response, while case validation, input inspection, and initial retrieval occur outside
   that exception boundary and can propagate as transport-level failures.

These compromises are recorded rather than hidden. Removing them before Phase 4 is optional unless
they threaten experimental validity, security, or maintainability.

## Architecture verification expectations

`tests/architecture/test_baseline_boundaries.py` must fail when:

- a declared Phase 3 layer is missing;
- `app.domain` imports an outer application package;
- `app.application.baseline` imports API, compatibility, Phase 4 governance, infrastructure,
  persistence, RAG, tool, composition, or process-entry modules;
- the baseline API entry points import concrete baseline, governance, or outbound adapters instead
  of the application boundary;
- removed compatibility paths are recreated or imported.

These static checks protect dependency direction. They do not replace code review, runtime tests,
threat modeling, or the cryptographic freeze procedure described in
[Phase 3 baseline](phase-3-baseline.md).
