# Phase 6 Experimental Protocol

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
