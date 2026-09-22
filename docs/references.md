# Project References

This bibliography consolidates the primary research, standards, security guidance, and official
technical documentation that inform Phases 3–6. Phase-specific documents explain how individual
sources apply to particular design decisions; this file provides one reviewer-facing index.

Sources were last checked on **22 September 2026**. Version-sensitive implementation behaviour is
governed by the repository's `uv.lock` files and frozen manifests, not by whatever version an
external documentation site displays later. References to NIST, OWASP, ISO, and SLSA describe
design guidance only and do not claim certification or formal conformity.

At the review date, NIST identifies AI RMF 1.0 as under revision, while FIPS 180-4 remains the
published Secure Hash Standard with a revision planned. The project therefore cites the specific
versions against which it was designed rather than silently substituting future revisions. SLSA
v1.2 is the current approved SLSA specification.

## Foundations: RAG and agentic architecture

[1] P. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in Advances in Neural Information Processing Systems 33, 2020, pp. 9459–9474. [Online]. Available: https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html [Accessed: Jul. 14, 2026].

[2] S. Yao et al., “ReAct: Synergizing reasoning and acting in language models,” in Proc. Int. Conf. Learn. Representations, 2023. [Online]. Available: https://arxiv.org/abs/2210.03629 [Accessed: Jul. 14, 2026].

[3] A. Cockburn, “Hexagonal architecture,” 2005. [Online]. Available: https://alistair.cockburn.us/hexagonal-architecture/ [Accessed: Jul. 15, 2026].

[4] Software, Systems and Enterprise—Architecture Description, ISO/IEC/IEEE Standard 42010:2022, Nov. 2022. [Online]. Available: https://www.iso.org/standard/74393.html [Accessed: Jul. 15, 2026].

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


## Phase 4: governance, security, and assurance

17. E. Tabassi, *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST AI
    100-1, 2023. [https://doi.org/10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1).
18. C. Autio *et al.*, *Artificial Intelligence Risk Management Framework: Generative Artificial
    Intelligence Profile*, NIST AI 600-1, 2024. [https://doi.org/10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1).
19. M. Souppaya, K. Scarfone, and D. Dodson, *Secure Software Development Framework (SSDF)
    Version 1.1*, NIST SP 800-218, 2022. [https://doi.org/10.6028/NIST.SP.800-218](https://doi.org/10.6028/NIST.SP.800-218).
20. OWASP Foundation, “AI Agent Security Cheat Sheet,” *OWASP Cheat Sheet Series*. [Guidance](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).
21. OWASP GenAI Security Project, *OWASP Top 10 for Agentic Applications 2026*, 2025.
    [Guidance](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/).
22. OWASP GenAI Security Project, “LLM06:2025 Excessive Agency.” [Guidance](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).
23. OWASP Foundation, “Logging Cheat Sheet,” *OWASP Cheat Sheet Series*. [Guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).
24. OWASP Foundation, “Input Validation Cheat Sheet,” *OWASP Cheat Sheet Series*. [Guidance](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html).

## Phase 5: evaluation contracts and provenance

25. JSON Schema, “JSON Schema Specification, Draft 2020-12.” [Specification](https://json-schema.org/specification).
26. A. Rundgren, B. Jordan, and S. Erdtman, “JSON Canonicalization Scheme (JCS),” RFC 8785,
    2020. [https://doi.org/10.17487/RFC8785](https://doi.org/10.17487/RFC8785).
27. National Institute of Standards and Technology, *Secure Hash Standard (SHS)*, FIPS PUB
    180-4, 2015. [https://doi.org/10.6028/NIST.FIPS.180-4](https://doi.org/10.6028/NIST.FIPS.180-4).
28. SLSA, “Provenance,” *SLSA Specification v1.2*. [Specification](https://slsa.dev/spec/v1.2/provenance).
29. I. Ward, “JSON Lines.” [Format documentation](https://jsonlines.org/).
30. Microsoft, “Autonomous service agents in Dynamics 365,” *Microsoft Learn*. [Documentation](https://learn.microsoft.com/en-us/dynamics365/contact-center/administer/autonomous-agents-overview).
31. ServiceNow, “Approval assistance AI agent,” *ServiceNow Product Documentation*. [Documentation](https://www.servicenow.com/docs/r/intelligent-experiences/plat-approval-assistance-ai-agent.html).

> NOTE: The Microsoft and ServiceNow sources support the realism of synthetic routing, case-management,
knowledge, approval, and escalation scenarios. They are illustrative enterprise-domain sources,
not evidence that this project reproduces either commercial platform.

## Phase 6: experimental design, statistics, and secondary evaluation

32. OpenAI, “Evaluate agent workflows,” *OpenAI API Documentation*. [Guide](https://developers.openai.com/api/docs/guides/agent-evals).
33. S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, “RAGAs: Automated Evaluation of
    Retrieval Augmented Generation,” in *Proceedings of EACL 2024: System Demonstrations*,
    pp. 150–158, 2024. [https://doi.org/10.18653/v1/2024.eacl-demo.16](https://doi.org/10.18653/v1/2024.eacl-demo.16).
34. Ragas, “Faithfulness,” *Ragas Documentation*. [Metric documentation](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).
35. Ragas, “LLMs,” *Ragas API Reference*. [API reference](https://docs.ragas.io/en/stable/references/llms/).
36. LangChain, “`langchain-community`,” *LangChain Python Reference*. [API reference](https://reference.langchain.com/python/langchain-community).
37. B. Efron and R. Tibshirani, “Bootstrap Methods for Standard Errors, Confidence Intervals,
    and Other Measures of Statistical Accuracy,” *Statistical Science*, vol. 1, no. 1,
    pp. 54–75, 1986. [https://doi.org/10.1214/ss/1177013815](https://doi.org/10.1214/ss/1177013815).
38. SciPy Community, “`scipy.stats.bootstrap`,” *SciPy API Reference*. [Documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
39. scikit-learn developers, “`fbeta_score`,” *scikit-learn API Reference*. [Documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.fbeta_score.html).
40. NIST/SEMATECH, “Randomized Block Designs,” *e-Handbook of Statistical Methods*.
    [Handbook](https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc332.htm).
41. Python Software Foundation, “`secrets` — Generate secure random numbers for managing
    secrets,” *Python Documentation*. [Documentation](https://docs.python.org/3/library/secrets.html).
42. Python Software Foundation, “`asyncio` — Asynchronous I/O,” *Python Documentation*.
    [Documentation](https://docs.python.org/3/library/asyncio.html).

> NOTE: Ragas faithfulness is used only as a secondary diagnostic in Phase 6. The preregistered primary
metrics and human adjudication remain authoritative; the Ragas paper or library documentation does
not replace the project's frozen scoring rubric.

## Reproducibility, testing, and reporting

43. Astral, “Locking and syncing,” *uv Documentation*. [Documentation](https://docs.astral.sh/uv/concepts/projects/sync/).
44. Pydantic Services Inc., “HTTPX2,” *HTTPX2 Documentation*. [Documentation](https://pydantic.dev/docs/httpx2/get-started/).
45. pytest contributors, “pytest Documentation.” [Documentation](https://docs.pytest.org/en/stable/).
46. Astral, “Ruff Documentation.” [Documentation](https://docs.astral.sh/ruff/).
47. J. Lehtosalo *et al.*, “mypy Documentation.” [Documentation](https://mypy.readthedocs.io/en/stable/).
48. Microsoft, “Pyright Documentation.” [Documentation](https://microsoft.github.io/pyright/).
49. W3C Web Accessibility Initiative, “Providing Accessible Names and Descriptions,”
    *ARIA Authoring Practices Guide*. [Guidance](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/).
50. Mozilla, “`<table>`: The Table element,” *MDN Web Docs*. [Documentation](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/table).
51. Mozilla, “`<svg>`,” *MDN Web Docs*. [Documentation](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/svg).

