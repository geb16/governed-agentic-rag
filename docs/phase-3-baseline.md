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
