# Start here 📌

The three most important docs for understanding and continuing this project. Read in this order.

| # | doc | what it gives you |
|---|---|---|
| 1 | **[FINDINGS.md](FINDINGS.md)** | the *results*: headline accuracy + cost tables, the empty-gold caveat, and the one command to reproduce any of it |
| 2 | **[FUNCTIONALITY.md](FUNCTIONALITY.md)** | the *system*: how to run experiments, read results, the backup/sharding/actor-critic machinery, where API keys + constants live |
| 3 | **[EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)** | the *what & why*: every experiment E0→E1.11, what we ran vs didn't, and the decision chain that got us here |
| 4 | **[prompt_structure.md](prompt_structure.md)** | the *prompt*: exactly what the agent sees and where skills are injected |

**Crunch any experiment's numbers yourself:** `python scripts/crunch_results.py experiments/<folder>`
→ accuracy, non-empty-gold split, side-effects, and cost ($/query, $/correct).

**One-line project summary.** Reduce tool-interaction failures in LLM agents on WorkBench with a
*leakage-safe* method — gated tool-interaction skills + an actor-critic verify-and-correct mechanism —
and honest reporting (non-empty-gold split), now being tested for generalization across models and
datasets.

**Fastest path to running something:** FUNCTIONALITY.md §12 (Quickstart).

---
*Other docs* (`docs/`, not onboarding-critical): `paper_review.md`, `experiment_plan.md`,
`reporting_standard.md`, `retrieval_design.md`, `workbench_and_integration_tests.md`, `writeup.md`,
`status.md`.
