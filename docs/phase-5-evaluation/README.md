# Phase 5 dataset release

Phase 5 is an offline evaluation-data layer. It does not modify or import into either
frozen runtime. The baseline and governed systems receive identical request objects,
case fixtures, knowledge, simulated tools, fault schedules, and model configuration.

## Scope and claim

Version `1.0.0` contains 100 fully synthetic enterprise-support cases:

| Primary stratum | Cases |
| --- | ---: |
| Normal | 17 |
| Ambiguous | 16 |
| Policy-sensitive | 17 |
| High-risk | 17 |
| Missing information | 16 |
| Tool failure | 17 |

Twenty cases are assigned to `validation` for harness verification and rubric
calibration. The remaining 80 are assigned to `test`. Test labels must remain unchanged
after comparative evaluation begins.

This is a production-grade **research artifact**. It is not production data and not evidence
that the sample represents every enterprise deployment. It is deployment-like within
the declared synthetic support domain. It contains no personal, customer, employee, or
confidential business data.

The near-balanced primary strata deliberately over-sample rare but costly failures. This
is a stratified challenge set, not a prevalence sample. Its raw aggregate result must not
be interpreted as the expected success or incident rate in a live support population.

## Reference and Evidence basis

The design follows these current primary sources:

- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) calls for
  repeatable TEVV, documented test sets and tools, conditions similar to deployment,
  safe failure, security/resilience evaluation, and transparency/accountability measures.
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
  motivates agent-goal hijack, tool misuse, identity, and unsafe-autonomy cases.
- [OWASP Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
  motivates least-functionality, complete-mediation, human-approval, and tool logging probes.
- [ServiceNow CSM agentic workflows](https://www.servicenow.com/docs/r/xanadu/customer-service-management/now-assist-for-csm/csm-ai-agents-use-cases.html)
  cover case validation, retrieval, transactional requests, and human escalation.
- [Microsoft Service Agent](https://learn.microsoft.com/en-us/dynamics365/customer-service/use/use-service-agent)
  covers case review, knowledge retrieval, summaries, status changes, and case actions.
- [OpenAI's support implementation](https://openai.com/index/openai-support-model/)
  describes support actions including refunds and incident lookups plus traces and evals.
- [OpenAI contextual-eval guidance](https://openai.com/index/evals-drive-next-chapter-of-ai/)
  recommends workflow-specific real-world examples, rare costly edge cases, and human audit.
- [OpenAI deployment simulation research](https://openai.com/index/deployment-simulation/)
  supports deployment-like contexts and realistic simulated tool environments.

> *Note*: External sources inform scenario realism and evaluation method only. Gold policy decisions
come exclusively from the frozen files in `data/knowledge_base` and frozen tool contracts.
