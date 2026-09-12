# Phase-6 Experimental Protocol

## Design

The experiment is a paired repeated comparison over the frozen 100-case Phase 5 dataset. Twenty
validation cases produce 120 observations; 80 untouched test cases produce 480 observations. Each
case is run three times in each condition. The fixed seed `20260831` alternates first condition by
case and repetition to reduce order effects.

The independent variable is the presence of the governance-aware workflow layer. Controlled
substrates are the model identifier, synthetic knowledge base, Qdrant collection, per-case SQLite
fixture, simulated tools, fault plan, request, and labels. Acquisition concurrency is one. An
accepted model invocation is never rerun. An atomic per-attempt journal is created before system
execution, acceptance is recorded after the first successful provider response, and only an
explicitly completed pre-acceptance failure can be retried, at most twice in total. A process
interruption leaving an attempt started or accepted but without a raw observation fails closed.
Authentication, connection, timeout, and provider-availability failures are invalid only when the
acceptance boundary proves that no provider response was received. Every failure after acceptance
is retained as a system outcome and scored under the frozen rubric.

## Sequence and leakage controls

1. Verify all inherited freezes and the locked environment.
2. Run validation, generate blinded reviews, resolve defects in the harness only, and record any
   protocol deviation. If code changes, rerun validation with the final candidate harness before
   freezing it; never carry validation evidence forward from superseded code.
3. Content-address the complete harness, pin the final validation manifest and summary, and
   preregister exactly one test run ID.
4. Atomically consume that authorization before any provider call, then run the untouched test
   split once. An interrupted test acquisition is not restarted under another run ID.
5. Complete dual independent, condition-blinded human review for every applicable decision field
   before opening comparative results. Resolve each disagreement explicitly.
6. Run Ragas as a secondary sensitivity measure, compute the registered estimates, and seal the
   sanitized artifact set.

Raw observations, normalized observations, metric contributions, estimates, paired differences,
usage, latency, review packets, resolved decisions, a deterministic HTML analysis report, and a
content-addressed manifest are retained.
Secrets are excluded from manifests and sensitive-key fields are redacted during sealing. Each run
manifest binds the non-secret runtime settings, exact allowlisted tool schemas, and a logical Qdrant
snapshot containing every point identifier, payload, and vector. Acquisition fails closed if the
configured collection is empty, and repeating a run detects any identity drift.
Before sealing, the harness validates the exact scheduled observation identities and independently
rederives every primary result artifact. A stored count, status, or summary is never sufficient
evidence of a valid result.

The implementation separates these controls by lifecycle responsibility. `composition/` prepares
run identity and wires acquisition; `experiment_control/` verifies readiness, freezes the harness,
and consumes the one-time test authorization; `reporting/` derives primary artifacts and runs
optional secondary grading; and `release/` independently verifies, sanitizes, and seals the final
test result. Package `__init__.py` files provide stable APIs for the CLI scripts.

## Registered analysis rules

- Report all 14 Phase 5 metrics separately; do not construct a post-hoc composite.
- Use case-clustered, two-sided 95% nonparametric percentile intervals with 10,000 replicates and
  seed `20260830`. Preserve category sizes only for overall and category-macro estimates; resample
  category, route, intent, and risk results within the selected stratum.
- Report the unweighted mean of the six primary-category estimates as `category_macro`; it is not
  estimable if any constituent category is not estimable.
- Compute treatment effects as governed minus baseline from complete case-by-repetition pairs. Do
  not impute invalid or missing members.
- Report a zero-denominator ratio as `NA`. Omit zero-denominator bootstrap replicates and report an
  interval only when at least 9,500 valid replicates remain.
- Treat all intervals as descriptive and pointwise. Perform no null-hypothesis tests, multiplicity
  adjustment, or post-hoc metric/stratum selection.

NIST calls for documented test sets, metrics, tools, uncertainty, and testing under deployment-like
conditions. Modern agent evaluation also distinguishes final-output quality from process and tool
behavior. This protocol is grounded in the following requirements:
[NIST AI RMF Measure 2.1 and 2.3](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/),
[Microsoft Foundry agent evaluators](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/agent-evaluators),
and [OpenAI agent evals](https://developers.openai.com/api/docs/guides/agent-evals).

> Note: The harness is local and provider-neutral. It does not depend on the legacy hosted OpenAI Evals API,
which the official guidance marks for shutdown in November 2026.
