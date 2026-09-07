# Phase 6 Limitations

- The synthetic setting improves control and privacy but cannot establish production generalization.
- Three stochastic repetitions estimate model variability only coarsely.
- Sequential execution reduces interference but does not measure production concurrency behavior.
- Human claim-support and route labels can disagree; dual review and explicit resolution reduce but
  do not eliminate subjectivity.
- LLM-based Ragas grading is nondeterministic and is secondary only.
- Audit completeness rewards the presence of registered facts, not their organizational usefulness.
- Simulated tools, approvals, faults, and local SQLite state do not reproduce distributed identity,
  authorization, transaction, or recovery systems.
- A single model and knowledge base limit external validity. Results support a controlled comparison,
  not a universal claim about all enterprise agents.
