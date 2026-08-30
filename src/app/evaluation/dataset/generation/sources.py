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

        ],
    }
