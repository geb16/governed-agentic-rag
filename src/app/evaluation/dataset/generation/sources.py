# Trusted source registry used to justify scenario and evaluation design.

# URLs and source-use statements are kept intact in the generated registry.
# ruff: noqa: E501

from typing import Any


def build_sources() -> dict[str, Any]:
    """Return sources; these inform realism but never override local gold policy."""
    return {
        "schema_version": 1,
        "reviewed_on": "2026-08-26",
        "policy_authority": (
            "Only the frozen files in data/knowledge_base determine case policy labels. "
            "External sources inform scenario archetypes, security coverage, and methodology."
        ),
        "sources": [
            {
                "source_id": "nist-ai-rmf",
                "publisher": "NIST",
                "title": "AI Risk Management Framework Core and NIST AI 600-1",
                "url": "https://airc.nist.gov/airmf-resources/airmf/5-sec-core/",
                "use": "Repeatable TEVV, deployment-like conditions, safe failure, security, and accountability.",
            },
            {
                "source_id": "owasp-agentic-top10",
                "publisher": "OWASP GenAI Security Project",
                "title": "OWASP Top 10 for Agentic Applications 2026",
                "url": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",
                "use": "Agent goal hijack, tool misuse, identity abuse, and unsafe autonomy coverage.",
            },
            {
                "source_id": "owasp-excessive-agency",
                "publisher": "OWASP GenAI Security Project",
                "title": "LLM06:2025 Excessive Agency",
                "url": "https://genai.owasp.org/llmrisk/llm062025-excessive-agency/",
                "use": "Least functionality, complete mediation, human approval, and logging scenarios.",
            },
            {
                "source_id": "servicenow-csm",
                "publisher": "ServiceNow",
                "title": "Using agentic workflows in Customer Service Management",
                "url": "https://www.servicenow.com/docs/r/xanadu/customer-service-management/now-assist-for-csm/csm-ai-agents-use-cases.html",
                "use": "Case triage, validation, knowledge retrieval, transactional work, and escalation archetypes.",
            },
            {
                "source_id": "servicenow-approval-agent",
                "publisher": "ServiceNow",
                "title": "Approval assistance AI agent",
                "url": "https://www.servicenow.com/docs/r/intelligent-experiences/plat-approval-assistance-ai-agent.html",
                "use": "Current approval retrieval, checklist, approve/reject, and role-bound workflow realism.",
            },
            {
                "source_id": "microsoft-service-agent",
                "publisher": "Microsoft",
                "title": "Use Service Agent in Customer Service",
                "url": "https://learn.microsoft.com/en-us/dynamics365/customer-service/use/use-service-agent",
                "use": "Knowledge-grounded case review, summarization, status update, and case action realism.",
            },
            {
                "source_id": "openai-support",
                "publisher": "OpenAI",
                "title": "Improving support with every interaction at OpenAI",
                "url": "https://openai.com/index/openai-support-model/",
                "use": "Support refunds, incident lookups, traces, classifiers, and continuous evaluation.",
            },
            {
                "source_id": "openai-contextual-evals",
                "publisher": "OpenAI",
                "title": "How evals drive the next chapter in AI for businesses",
                "url": "https://openai.com/index/evals-drive-next-chapter-of-ai/",
                "use": "Contextual workflow evals, real-world examples, costly edge cases, and human audit.",
            },
            {
                "source_id": "openai-deployment-simulation",
                "publisher": "OpenAI",
                "title": "Predicting model behavior before release by simulating deployment",
                "url": "https://openai.com/index/deployment-simulation/",
                "use": "Deployment-like prompts, isolated state, and realistic simulated tool failure trajectories.",
            },
        ],
    }
