# Architecture

```text
POST /api/v1/baseline/invoke
          |
          v
 API authentication + request/schema bounds
          |
          v
 case-id validation + isolated synthetic state
          |
          v
 deterministic input guardrail
          |
          v
 synthetic KB retriever (lexical | Qdrant)
          |
          v
 bounded Responses API agent loop
          |
          +---- proposes one strict tool call ----+
          |                                       |
          |                         allowlist + Pydantic validation
          |                                       |
          |                  case-bound simulated execution
          |                                       |
          +---- action outcome + evidence <-------+
          |
          v
 Pydantic final output + citation/output guardrail
          |
          v
 BaselineResponse + evidence/action contracts + basic JSON execution logs
```

## Extension seams

- `ModelGateway` isolates the model provider from application orchestration.
- `RetrievalGateway` isolates retrieval; `KnowledgeRetriever` supports lexical and vector paths.
- `ControlledTool` plus `ToolRouter` isolates capabilities and enforcement.
- `SyntheticRepository` isolates shared business state and case-scoped fault plans.
- `build_shared_tools` defines one capability registry for both experimental conditions.
- Pydantic request, tool, result, and response contracts are explicit integration boundaries.
- The `BaselineUseCase` boundary can later be wrapped by a workflow layer without changing frozen
  baseline behavior. `BaselineAgent` is only the constructor-compatible façade.

No class in this layer models governance state. Phase 4 should compose around the invocation
boundary rather than inserting policy decisions into the baseline.

## Experimental boundary

The shared substrate owns model access, retrieval, synthetic business state, tool schemas,
fault injection, application security, and governance-neutral outcomes. The baseline owns only
its direct LLM agent loop and prompt-level business behaviour. Phase 4 may add classification,
risk checks, approval routing, workflow retry/recovery, durable workflow state, and structured
audit events without changing the frozen baseline implementation.
