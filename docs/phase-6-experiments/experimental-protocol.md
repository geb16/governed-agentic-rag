# Phase-6 Experimental Protocol

## Design

The experiment is a paired repeated comparison over the frozen 100-case Phase 5 dataset. Twenty
validation cases produce 120 observations; 80 untouched test cases produce 480 observations. Each
case is run three times in each condition. The fixed seed `20260831` alternates first condition by
case and repetition to reduce order effects.

The independent variable is the presence of the governance-aware workflow layer. Controlled
substrates are the model identifier, synthetic knowledge base, Qdrant collection, per-case SQLite
fixture, simulated tools, fault plan, request, and labels. Acquisition concurrency is one. An
accepted model invocation is never rerun; only a failure before request acceptance can be retried,
at most twice in total.

## Sequence and leakage controls

1. Verify all inherited freezes and the locked environment.
2. Run validation, generate blinded reviews, resolve defects in the harness only, and record any
   protocol deviation.
3. Freeze the harness configuration and adjudication instructions.
4. Run the untouched test split once.
5. Complete dual independent, condition-blinded human review before opening comparative results.
6. Run Ragas as a secondary sensitivity measure, compute the registered estimates, and seal the
   sanitized artifact set.

Raw observations, normalized observations, metric contributions, estimates, paired differences,
usage, latency, review packets, resolved decisions, and a content-addressed manifest are retained.
Secrets are excluded from manifests and sensitive-key fields are redacted during sealing.

NIST calls for documented test sets, metrics, tools, uncertainty, and testing under deployment-like
conditions. Modern agent evaluation also distinguishes final-output quality from process and tool
behavior. This protocol is grounded in the following requirements:
[NIST AI RMF Measure 2.1 and 2.3](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/),
[Microsoft Foundry agent evaluators](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/agent-evaluators),
and [OpenAI agent evals](https://developers.openai.com/api/docs/guides/agent-evals).
