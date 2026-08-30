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
        ],
    }
