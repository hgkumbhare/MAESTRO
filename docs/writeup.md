# MAESTRO — Findings Writeup (working draft)

A running synthesis of the project's findings and the headline result, structured so it can
grow into the paper. Numbers are from the actual runs (gpt-4o-mini, smolagents, temp 0, seed 42).
Living doc — edit freely. Detailed per-experiment records live in `experiments/E*/RESULTS.md`;
the issue tracker is `docs/paper_review.md`.

---

## Summary (one paragraph)
We study reducing **tool-interaction hallucinations** in LLM agents on WorkBench. We first show
the prior "integration-test" method **leaks** (it reproduces eval templates, inflating accuracy by
memorization). We replace it with a **leakage-safe library of tool-interaction skills** — short,
dataset-agnostic rules ("resolve an identifier before using it", "map every task constraint into
the search filters") — injected **only when a per-query trigger fires** (an LLM classifier decides
which skills apply). On the team-comparable improved-tools baseline, trigger-gated skills improve
**real-task accuracy by +11.2** (44.4→55.6) and **reduce harmful actions** (fixing 33% of the
base's side-effects), while a naive always-on variant regresses several domains. We also surface a
**benchmark artifact**: WorkBench aggregate accuracy rewards *inaction* on "empty-gold" queries, so
a more capable agent is penalized — the honest metric is accuracy on non-empty queries.

---

## 1. The problem and the leaky baseline
- **Tool hallucination:** agents pick wrong tools, fabricate/omit parameters, or claim actions they
  never executed. WorkBench = 5 domains, ~27 tools, 690 tasks, outcome-based scoring.
- **Prior method ("improved + integration tests")** appends integration-test *source code* into tool
  descriptions. We found this **leaks**: 5 of 8 PM eval templates (and real entities) are reproduced
  in the tests. Measured on PM: **covered templates +24.0, uncovered +3.3 (noise)** → the gain is
  memorization of in-distribution solutions, not generalization. [E0; paper_review S3]

## 2. Approach — leakage-safe tool-interaction skills
- A **skill** = a short rule teaching a tool-use competence (identifier-resolution, fetch-before-act,
  reuse-returned-value, no-duplicate-calls, read-output, parameter-completeness, right-tool-selection,
  tool-required). Derived from the failure taxonomy (paper §2.1). **Dataset-agnostic** — no eval
  entities/templates — so leakage-safe by construction.
- Injected into the agent's task prompt (see `docs/prompt_structure.md`). Two variants:
  - **always-on** (E1): inject all skills every query.
  - **gated** (E1.5.5+): an **LLM classifier** decides which skills' triggers apply to *this query*;
    inject only those. Flat/simple queries get **zero** skills → no perturbation.

## 3. Always-on → gated (why gating matters)
- **Always-on (E1, original tools):** overall +2.5, but MIXED — helped chained domains
  (calendar +12.7, PM +6.2, email +3.3) yet **hurt flat query domains** (analytics −2.5, CRM −3.7).
  Diagnosis: the irrelevant dependency-chain skills perturb parameterization on single-tool queries.
- **Gated (E1.5.5, original tools):** overall **48.7 (best)**; fixed the analytics/CRM regressions
  (they get 0 skills), email jumped to 60.0. A PM regression appeared — see §5/S7.

## 4. Two corrections that produced the headline result
1. **Parameter-completeness skill (v3).** Diagnosing the PM regression revealed the agent omits a
   stated filter (`list_name="In Progress"`) → searches by identity only → acts on all records. We
   added a general skill ("map every task constraint into the search args") — failure mode #7 in the
   taxonomy. [E1.6]
2. **Tool baseline aligned to the team: improved tools.** The team runs `--use_improved_tools`
   (rewritten descriptions, NO integration tests). We verified our `base` ≡ that command
   param-for-param, aligned temperature to 0, and added `seed=42` for reproducibility (same query
   twice → identical). **Improved tools substantially raise the base** (overall 44.9→50.6; PM
   38.8→61.3) because the descriptions already teach email lookup + filtering.

## 5. Headline result — E1.7 (improved tools, temp 0 + seed 42)
**base vs trigger-gated skills, all domains:**

| domain | n | base % | gated % | Δ acc | base se% | gated se% | Δ se |
|---|---|---|---|---|---|---|---|
| email | 90 | 61.1 | 85.6 | **+24.4** | 34.4 | 5.6 | **−28.9** |
| CRM | 80 | 42.5 | 55.0 | **+12.5** | 40.0 | 40.0 | 0.0 |
| project_management | 80 | 61.3 | 70.0 | **+8.7** | 16.2 | 25.0 | +8.8 |
| analytics | 120 | 30.0 | 35.0 | +5.0 | 58.3 | 53.3 | −5.0 |
| calendar | 110 | 80.0 | 82.7 | +2.7 | 13.6 | 16.4 | +2.7 |
| multi_domain | 210 | 41.4 | 43.3 | +1.9 | 48.6 | 49.5 | +1.0 |
| **OVERALL** | 690 | **50.6** | **58.1** | **+7.5** | 38.1 | 35.2 | **−2.9** |

**Side-effect improvement:** of 263 queries where base took a harmful action, gated **fixed 87
(33%)**, introduced 67, **net −20 (safer)**.

**Every domain's accuracy improves — no regressions.** PM now *helps* (+8.7): on improved tools the
base already resolves emails, so parameter-completeness adds filtering cleanly.

**Key comparison:** gated adds **+7.5 over the stronger improved-tools base** — *larger* than its
+3.8 over the weaker original base. Skills add value even when the base is already capable.

## 6. The benchmark artifact (empty-gold) — S7
Splitting E1.7 by whether the gold answer is empty:

| subset | n | base acc | gated acc | base se | gated se |
|---|---|---|---|---|---|
| **non-empty (real tasks)** | 568 | 44.4 | **55.6 (+11.2)** | 41.9 | **36.3 (−5.6)** |
| empty ("do nothing") | 122 | 79.5 | 69.7 (−9.8) | 20.5 | 30.3 (+9.8) |

WorkBench has many "do nothing" tasks (person has no matching records). A **less capable** agent
(fails to resolve the identifier) does nothing → scores correct; a **more capable** agent resolves
it, acts, and is penalized. So **aggregate accuracy rewards inaction** and understates skills' value.
The honest headline is **+11.2 accuracy / −5.6 side effects on real tasks**. This is a WorkBench
design caveat worth stating, and it re-frames how tool-agent benchmarks should be scored.

## 7. Methodology & reproducibility
- **Leakage-safe by construction** (skills contain no eval entities/templates) + an audit gate
  (`experiments/common/audit.py`) for any example-based work; dev/test discipline for anything
  derived from observed failures.
- **Determinism:** temp 0 + `seed=42` (agent + gate); verified identical output on repeat.
- **Team-comparable:** `base` ≡ `--use_improved_tools --agent_engine=smolagents` (verified;
  empirically 10/10 same correctness at temp 0).
- **Infra:** config-driven runner, config-keyed done-store (resumable across shard counts /
  interruptions), size-balanced parallel sharding, per-run cost/token/latency, honest reporting
  (per-domain, split by gold, side-effect rate). Docs: `experiment_plan.md`, `reporting_standard.md`,
  `retrieval_design.md`.

## 8. Limitations & next steps
- **Single model** (gpt-4o-mini). Multi-model (gpt-4o, llama, qwen) would support "any model" (S1).
- **Gate is stochastic** — the LLM classifier occasionally mis-fires; a small held-out-tuned or
  ensembled gate could tighten it.
- **Empty-gold artifact** — report non-empty as primary; consider a restraint-specific metric.
- **Cross-dataset (E7):** the strongest generalization test — do WorkBench-learned skills transfer to
  API-Bank? (leakage-proof by construction). Not yet run.
- **Example bank + retrieval (E3/E4)** and **bottom-up skill derivation (E8)** remain to strengthen.

---

## Appendix — experiment ledger
| exp | what | tools | headline |
|---|---|---|---|
| E0 | leaky integration tests | orig | covered +24 / uncovered +3.3 → leakage |
| E1 | always-on skills | orig | +2.5 overall, mixed (hurts flat domains) |
| E1.5 | embedding gate | — | fragile (parked) |
| E1.5.5 | LLM-gated skills (7-card) | orig | +3.8 overall (48.7); PM artifact found |
| E1.6 | + parameter-completeness | improved | setup/transition record |
| **E1.7** | **gated skills (v3)** | **improved** | **+7.5 overall / +11.2 real-task; −2.9 se** |
