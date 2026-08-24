# Phase 4 governance tests

Phase 4 tests are isolated from the frozen baseline suite and grouped by verification scope:

```text
tests/governance/
|-- unit/          Manifest, security, and deterministic primitives
|-- component/     Individually composed governance stages
|-- integration/   Workflow, API, audit, rollback, and restart behavior
|-- architecture/  Static dependency-direction rules
`-- support.py     Phase 4-only model doubles and composition helpers
```

Run the complete repository suite before review:

```console
uv run pytest
```

Focused commands remain useful during development:

```console
uv run pytest tests/governance/unit
uv run pytest tests/governance/component
uv run pytest tests/governance/integration
uv run pytest tests/governance/architecture
```

The directory package markers are intentional: they give test modules qualified import names and
prevent collisions with same-named Phase 3 tests such as `baseline/integration/test_api.py`.
