# Project References

This bibliography consolidates the primary research, standards, security guidance, and official
technical documentation that inform Phases 3–7(baseline, governance, evaluation, experiment and analysis). Phase-specific documents explain how individual
sources apply to particular design decisions; this file provides one reviewer-facing index.

Sources were last checked on **22 September 2026**. Version-sensitive implementation behaviour is
governed by the repository's `uv.lock` files and frozen manifests, not by whatever version an
external documentation site displays later. References to NIST, OWASP, ISO, and SLSA describe
design guidance only and do not claim certification or formal conformity.

At the review date, NIST identifies AI RMF 1.0 as under revision, while FIPS 180-4 remains the
published Secure Hash Standard with a revision planned. The project therefore cites the specific
versions against which it was designed rather than silently substituting future revisions. SLSA
v1.2 is the current approved SLSA specification.

## Reference groups

- [Foundations: RAG and agentic architecture](#foundations-rag-and-agentic-architecture)
- [Phase 3: baseline implementation](#phase-3-baseline-implementation)
- [Phase 4: governance, security, and assurance](#phase-4-governance-security-and-assurance)
- [Phase 5: evaluation contracts and provenance](#phase-5-evaluation-contracts-and-provenance)
- [Phase 6: experimental design, statistics, and secondary evaluation](#phase-6-experimental-design-statistics-and-secondary-evaluation)
- [Reproducibility, testing, and reporting](#reproducibility-testing-and-reporting)

---

## Foundations: RAG and agentic architecture

[1] P. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in Advances in Neural Information Processing Systems 33, 2020, pp. 9459–9474. [Online]. Available: https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html [Accessed: Jul. 14, 2026].

[2] S. Yao et al., “ReAct: Synergizing reasoning and acting in language models,” in Proc. Int. Conf. Learn. Representations, 2023. [Online]. Available: https://arxiv.org/abs/2210.03629 [Accessed: Jul. 14, 2026].

[3] A. Cockburn, “Hexagonal architecture,” 2005. [Online]. Available: https://alistair.cockburn.us/hexagonal-architecture/ [Accessed: Jul. 15, 2026].

[4] Software, Systems and Enterprise—Architecture Description, ISO/IEC/IEEE Standard 42010:2022, Nov. 2022. [Online]. Available: https://www.iso.org/standard/74393.html [Accessed: Jul. 15, 2026].

---

## Phase 3: baseline implementation

[5] OpenAI, “Create a model response,” OpenAI API Reference. [Online]. Available: https://developers.openai.com/api/reference/python/resources/responses/methods/create [Accessed: Jul. 15, 2026].

[6] OpenAI, “Function calling,” OpenAI API Documentation. [Online]. Available: https://developers.openai.com/api/docs/guides/function-calling [Accessed: Jul. 16, 2026].

[7] OpenAI, “Vector embeddings,” OpenAI API Documentation. [Online]. Available: https://developers.openai.com/api/docs/guides/embeddings [Accessed: Jul. 16, 2026].

[8] S. Ramírez, “Lifespan events,” FastAPI Documentation. [Online]. Available: https://fastapi.tiangolo.com/advanced/events/ [Accessed: Jul. 20, 2026].

[9] Pydantic Services Inc., “Strict mode,” Pydantic Documentation. [Online]. Available: https://docs.pydantic.dev/latest/concepts/strict_mode/ [Accessed: Jul. 20, 2026].

[10] Pydantic Services Inc., “Settings management,” Pydantic Documentation. [Online]. Available: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ [Accessed: Jul. 20, 2026].

[11] Qdrant Solutions GmbH, “Query points,” Qdrant API Reference. [Online]. Available: https://api.qdrant.tech/api-reference/search/query-points [Accessed: Jul. 22, 2026].

[12] Qdrant Solutions GmbH, “Scroll points,” Qdrant API Reference. [Online]. Available: https://api.qdrant.tech/api-reference/points/scroll-points [Accessed: Jul. 22, 2026].

[13] Python Software Foundation, “sqlite3—DB-API 2.0 interface for SQLite databases,” Python 3 Documentation. [Online]. Available: https://docs.python.org/3/library/sqlite3.html [Accessed: Jul. 22, 2026].

[14] SQLite Project, “Transaction.” [Online]. Available: https://www.sqlite.org/lang_transaction.html [Accessed: Jul. 23, 2026].

[15] I. Levkivskyi, J. Lehtosalo, and Ł. Langa, “PEP 544—Protocols: Structural subtyping (static duck typing),” Python Enhancement Proposals, 2017. [Online]. Available: https://peps.python.org/pep-0544/ [Accessed: Jul. 28, 2026].

---

## Phase 4: governance, security, and assurance

[16] E. Tabassi, Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1, Jan. 2023, doi: 10.6028/NIST.AI.100-1. [Online]. Available: https://www.nist.gov/itl/ai-risk-management-framework [Accessed: Jul. 30, 2026].

[17] C. Autio et al., Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile, NIST AI 600-1, Jul. 2024, doi: 10.6028/NIST.AI.600-1.

[18] M. Souppaya, K. Scarfone, and D. Dodson, Secure Software Development Framework (SSDF) Version 1.1: Recommendations for Mitigating the Risk of Software Vulnerabilities, NIST SP 800-218, Feb. 2022, doi: 10.6028/NIST.SP.800-218.

[19] OWASP Foundation, “AI agent security cheat sheet,” OWASP Cheat Sheet Series. [Online]. Available: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html [Accessed: Aug. 01, 2026].

[20] OWASP GenAI Security Project, OWASP Top 10 for Agentic Applications 2026, Dec. 2025. [Online]. Available: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ [Accessed: Aug. 01, 2026].

[21] OWASP GenAI Security Project, “LLM06:2025 excessive agency,” 2025. [Online]. Available: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/ [Accessed: Aug. 01, 2026].

[22] OWASP Foundation, “Logging cheat sheet,” OWASP Cheat Sheet Series. [Online]. Available: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html [Accessed: Aug. 05, 2026].

[23] OWASP Foundation, “Input validation cheat sheet,” OWASP Cheat Sheet Series. [Online]. Available: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html [Accessed: Aug. 07, 2026].

---

## Phase 5: evaluation contracts and provenance

[24] JSON Schema, “JSON Schema specification, Draft 2020-12.” [Online]. Available: https://json-schema.org/specification [Accessed: Aug. 15, 2026].

[25] A. Rundgren, B. Jordan, and S. Erdtman, “JSON Canonicalization Scheme (JCS),” RFC 8785, Jun. 2020, doi: 10.17487/RFC8785.

[26] National Institute of Standards and Technology, Secure Hash Standard (SHS), FIPS PUB 180-4, Aug. 2015, doi: 10.6028/NIST.FIPS.180-4.

[27] SLSA Community, “Provenance,” SLSA Specification, ver. 1.2, Nov. 2025. [Online]. Available: https://slsa.dev/spec/v1.2/provenance [Accessed: Aug. 15, 2026].

[28] I. Ward, “JSON Lines.” [Online]. Available: https://jsonlines.org/ [Accessed: Aug. 17, 2026].

[29] Microsoft, “Use Service Agent in Customer Service,” Microsoft Learn. [Online]. Available: https://learn.microsoft.com/en-us/dynamics365/customer-service/use/use-service-agent [Accessed: Aug. 15, 2026].

[30] ServiceNow, “Customer service management AI agent use cases,” ServiceNow Product Documentation. [Online]. Available: https://www.servicenow.com/docs/r/xanadu/customer-service-management/now-assist-for-csm/csm-ai-agents-use-cases.html [Accessed: Aug. 21, 2026].

[31] ServiceNow, “Approval assistance AI agent,” ServiceNow Product Documentation. [Online]. Available: https://www.servicenow.com/docs/r/intelligent-experiences/plat-approval-assistance-ai-agent.html [Accessed: Aug. 21, 2026].

> **Scope note:** The Microsoft and ServiceNow sources support the realism of synthetic routing,
> case-management, knowledge, approval, and escalation scenarios. They are illustrative
> enterprise-domain sources, not evidence that this project reproduces either commercial platform.

---

## Phase 6: experimental design, statistics, and secondary evaluation

[32] OpenAI, “Improving support with every interaction at OpenAI,” 2025. [Online]. Available: https://openai.com/index/openai-support-model/ [Accessed: Aug. 26, 2026].

[33] S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, “RAGAs: Automated evaluation of retrieval augmented generation,” in Proc. 18th Conf. Eur. Chapter Assoc. Comput. Linguistics: System Demonstrations, 2024, pp. 150–158, doi: 10.18653/v1/2024.eacl-demo.16.

[34] Ragas, “Faithfulness,” Ragas Documentation. [Online]. Available: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ [Accessed: Sep. 02, 2026].

[35] Ragas, “LLMs,” Ragas API Reference. [Online]. Available: https://docs.ragas.io/en/stable/references/llms/ [Accessed: Sep. 02, 2026].

[36] OpenAI, “How evals drive the next chapter in AI for businesses,” 2025. [Online]. Available: https://openai.com/index/evals-drive-next-chapter-of-ai/ [Accessed: Aug. 26, 2026].

[37] B. Efron and R. Tibshirani, “Bootstrap methods for standard errors, confidence intervals, and other measures of statistical accuracy,” Statistical Science, vol. 1, no. 1, pp. 54–75, Feb. 1986, doi: 10.1214/ss/1177013815.

[38] C. J. van Rijsbergen, Information Retrieval, 2nd ed. London, U.K.: Butterworths, 1979. [Online]. Available: https://www.dcs.gla.ac.uk/Keith/Preface.html [Accessed: Sep. 03, 2026].

[39] NIST/SEMATECH, “Randomized block designs,” e-Handbook of Statistical Methods. [Online]. Available: https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc332.htm [Accessed: Sep. 03, 2026].

[40] Python Software Foundation, “secrets—Generate secure random numbers for managing secrets,” Python 3 Documentation. [Online]. Available: https://docs.python.org/3/library/secrets.html [Accessed: Sep. 04, 2026].

[41] Python Software Foundation, “`asyncio`—Asynchronous I/O,” Python Documentation. [Online]. Available: https://docs.python.org/3/library/asyncio.html [Accessed: Jul. 17, 2026].

[42] SciPy Community, “`scipy.stats.bootstrap`,” SciPy API Reference. [Online]. Available: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html [Accessed: Sep. 08, 2026].

[43] scikit-learn developers, “`fbeta_score`,” scikit-learn API Reference. [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.fbeta_score.html [Accessed: Sep. 08, 2026].

[44] LangChain, “langchain-community,” LangChain Python Reference. [Online]. Available: https://reference.langchain.com/python/langchain-community [Accessed: Sep. 02, 2026].

> **Method note:**
>
> 1. Ragas faithfulness is used only as a secondary diagnostic in Phase 6. The preregistered
>    primary metrics and human adjudication remain authoritative; the Ragas paper or library
>    documentation does not replace the project's frozen scoring rubric.
> 2. The percentile bootstrap and F-score calculations are implemented directly in
>    `application/statistics.py` and `application/scoring.py`. The *SciPy* and *scikit-learn*
>    references were used only for basic guidance.

---

## Reproducibility, testing, and reporting

[45] OpenAI, “Predicting model behavior before release by simulating deployment,” 2025. [Online]. Available: https://openai.com/index/deployment-simulation/ [Accessed: Aug. 26, 2026].

[46] Astral, “Locking and syncing,” uv Documentation. [Online]. Available: https://docs.astral.sh/uv/concepts/projects/sync/ [Accessed: Jun. 20, 2026].

[47] Pydantic Services Inc., “HTTPX2,” HTTPX2 Documentation. [Online]. Available: https://pydantic.dev/docs/httpx2/get-started/ [Accessed: Jul. 14, 2026].

[48] pytest contributors, “pytest documentation.” [Online]. Available: https://docs.pytest.org/en/stable/ [Accessed: Jul. 14, 2026].

[49] Astral, “Ruff documentation.” [Online]. Available: https://docs.astral.sh/ruff/ [Accessed: 20. 20, 2026].

[50] J. Lehtosalo et al., “mypy documentation.” [Online]. Available: https://mypy.readthedocs.io/en/stable/ [Accessed: Jul. 16, 2026].

[51] Microsoft, “Pyright documentation.” [Online]. Available: https://microsoft.github.io/pyright/ [Accessed: Jul. 15, 2026].

[52] pre-commit contributors, “pre-commit documentation.” [Online]. Available: https://pre-commit.com/ [Accessed: Jul. 15, 2026].

[53] W3C Web Accessibility Initiative, “Providing accessible names and descriptions,” ARIA Authoring Practices Guide. [Online]. Available: https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/ [Accessed: Aug. 01, 2026].

[54] Mozilla, “`<table>`: The Table element,” MDN Web Docs. [Online]. Available: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/table [Accessed: Sep. 10, 2026].

[55] Mozilla, “svg,” MDN Web Docs. [Online]. Available: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/svg [Accessed: Sep. 10, 2026].
