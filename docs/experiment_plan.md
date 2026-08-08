# Experiment Roadmap — ordered by least resistance → headline

Sequenced so each step is cheap, de-risks the next, and builds toward the cross-dataset
result. **The honesty meter for every experiment is the covered-vs-uncovered (or
held-out) split** — aggregate accuracy hides leakage (see
[paper_review.md](./paper_review.md) S3). Design context:
[retrieval_design.md](./retrieval_design.md).

**Baseline to beat (gpt-4o-mini, 80 PM queries):**
covered 36.0→60.0 (+24, leaked) · **uncovered 43.3→46.7 (+3.3) ← the number that matters**

**Status legend:** ⬜ not started · 🟡 in progress · ✅ done

---

## E0 — Leakage diagnostic  ✅ DONE (not re-run)
- **Question:** does the current "improved" method leak (memorize) rather than generalize?
- **Result:** YES. gpt-4o-mini, 80 PM queries: covered +24.0, uncovered +3.3 (≈1 query).
  Recorded in `experiments/E0_baselines/RESULTS.md` and `docs/paper_review.md` (S3).
- **Status:** diagnostic complete — this is *why the project pivoted*. **Not re-run.**
  We already know `improved` leaks; no value in re-confirming it.
- **What E0 provided is carried forward for free:** `base` (the universal control) and the
  PM covered/uncovered leakage guardrail are both produced *inside* E1's scope-agnostic run.

### Scope-agnostic after E0
E0 is the last PM-only step. **From E1 on, every experiment runs all domains** via a
config-driven runner and **reports per scope** (per domain; PM also split covered/uncovered
as a leakage guardrail). `base` is the **in-run control** of each experiment (deltas are
self-contained). `improved` is **demoted** to a documented leaky baseline — included only
when you deliberately want to quantify leakage cost (E3), and only on PM where it applies.
E7 (cross-dataset) is a separate *dataset* axis, not a domain scope.

## E0.5 — Eval-harness sanity across domains (fixes C1)  ⬜  ← promoted: unblocks E1
- **Question:** are Emails/Analytics/Calendar/Multi really 0%, or is the harness broken?
  (A single calendar query scored 100% — contradicts Table 2.)
- **Requires:** run gpt-4o-mini on a 5-query sample per domain; trace generation vs
  answer-matching vs DB-reset.
- **Success:** each domain either scores >0 or we find the harness bug.
- **Cost:** ~$0.1, ~30min. **De-risks:** all multi-domain evaluation. **Blocks:** E1(broad), E5.

### Why not PM-only from here on
PM is the only domain with an internal **covered/uncovered** control, so it is where we
*measure leakage*. But the other 4 domains (Email, Calendar, Analytics, CRM) have **zero
integration tests → they are a fully held-out, leakage-free evaluation set by default.**
Two grades of within-dataset held-out:
- **PM uncovered templates** → weak (same domain, held-out task type).
- **The 4 untouched domains** → stronger (held-out *domains*; cross-domain transfer).

Skills are domain-agnostic, so evaluating them only on PM undersells them. From E1 on,
**evaluate across all domains**: PM supplies the leakage split (honesty meter); the 4
untouched domains supply the clean generalization signal. E0.5 must clear first so those
domains are a trustworthy eval.

---

## E1 — Skills, scope-agnostic (Q3, no retrieval)  ⬜  ★ ENTRY POINT (first live experiment)
- **Question:** do leakage-safe **skill cards** lift held-out accuracy across all domains
  (and PM's uncovered split)?
- **Conditions:** `base` (in-run control), `skills`; **`improved` optional, PM-only** (the
  leaky baseline — include only if you want the head-to-head on PM).
- **Requires:**
  - ~7 **domain-agnostic** skill cards (`experiments/common/skills.py`, already authored).
  - a `skills` condition hook (inject all 7 into the system prompt; **no retrieval** at
    this size).
  - E0.5 cleared (so non-PM domains are a trustworthy eval).
- **Method:** scope-agnostic run over all domains; **report per scope** — per-domain
  `skills` vs `base`, plus PM covered/uncovered as a leakage guardrail.
- **Success:** ≥2 domains improve (`skills` vs `base`) AND PM covered ≈ uncovered gain
  (no leakage). If PM-covered ≫ uncovered → skills leaking, investigate.
- **Read-outs:** nothing rises → too abstract for 4o-mini → go to E2.
- **Cost:** ~$1–2, ~1–2h. Pilot on PM + Calendar first (Calendar verified working).
  **De-risks:** the entire skills thesis. **Depends:** E0.5. (E0 already done.)

## E2 — Skills + held-out micro-examples (grounding, Q1 touch)  ⬜ (conditional)
- **Question:** does one held-out concrete demo per skill help small models follow it?
- **Requires:** a fictional sandbox (held-out entities); attach 1 executable micro-demo to
  each skill card (sandbox values only).
- **Method:** compare skills-only (E1) vs skills+demo on uncovered split.
- **Success:** skills+demo > skills-only on uncovered. **Run only if E1 is weak/mixed.**
- **Cost:** ~$0.3, ~1h (mostly authoring). **Depends:** E1.

---

## E3 — Leakage-safe example bank + audit gate (Q1 done right)  ⬜
- **Question:** do **leakage-safe examples** beat skills — or the leaky current method — on
  the uncovered split?
- **Requires:**
  - **Audit gate** `check_example()` — entity blocklist + eval-template + semantic +
    answer checks, sourced from `data/processed/` (see retrieval_design §6.3). *Reusable,
    highest-leverage brick.*
  - fictional sandbox; generate examples **blind**, execute-then-store, filter by the gate.
- **Method:** base vs leaky-current vs skills(E1) vs clean-examples on covered/uncovered.
- **Success:** clean examples move **uncovered**; leaky-vs-clean gap quantifies memorization.
- **Cost:** ~$0.5 run + build effort (the gate + generation pipeline). **Depends:** E0, E1.

## E4 — Retrieval + ablations (scale the bank)  ⬜
- **Question:** once the bank is large, does **top-k retrieval** beat inject-all / random,
  and does accuracy scale with bank size?
- **Requires:** FAISS index + sentence-transformers (in requirements), retrieval +
  retrieval-time leakage guard.
- **Method:** k ∈ {0,1,3,5}; retrieved vs random-k vs static; bank-size 25/50/100.
- **Success:** retrieval > random; monotone-ish gain with bank size; plateau found.
- **Cost:** ~$1, ~2h. **Depends:** E3 (needs a bank big enough to retrieve from).

---

## E5 — Scale to all 5 domains, within-dataset  ⬜
- **Question:** does the best method (skills / clean-examples) generalize beyond PM?
- **Requires:** E0.5 resolved; run best condition on all domains (~690 queries), held-out
  split per domain.
- **Success:** held-out gains in ≥3 domains, not just PM. Directly rewrites Table 2.
- **Cost:** ~$2–4, ~half day. **Depends:** E0.5, and a winner from E1/E3.

## E6 — Multi-model  ⬜  (OPTIONAL — deferred)
- **Question:** do gains hold across models (supports "adaptable to any model", S1)?
- **Requires:** `openrouter_key.txt`; run best condition on gpt-4o, llama-3.3-70b,
  qwen-2.5 (repo already supports these).
- **Success:** positive held-out delta on ≥2 additional models.
- **Cost:** ~$3–8 (bigger models), ~half day. **Depends:** E5.
- **Status:** deferred — nice-to-have for the S1 claim, not load-bearing. Run late or skip.

---

## E7 — Cross-dataset transfer: WorkBench → API-Bank (Rung 3)  ⬜  ★ headline
- **Question:** do **WorkBench-learned skills** improve **API-Bank** with zero shared
  tools/entities/templates? (Leakage-proof generalization → C4.)
- **Requires:**
  - dataset-agnostic skill representation (triggers on param *semantics*, not tool names);
  - a thin **binding layer** mapping skills onto API-Bank's tools + call format + API-search;
  - API-Bank eval harness ([repo](https://github.com/hgkumbhare/DAMO-ConvAI/tree/main/api-bank)).
- **Method:** API-Bank base vs API-Bank + WorkBench-skills (Levels 1 & 2).
- **Success:** positive delta on API-Bank from skills never fit to it → the paper's headline.
- **Cost:** build-heavy; runs cheap. **Depends:** E1 (skills must work within-dataset first).

---

## E8 — Bottom-up skill derivation  ⬜  (strengthening; the Q4 quadrant)
- **Question:** do skills **derived from observed failures** match/beat the hand-written
  top-down skills (E1), and do they surface failure modes we didn't guess?
- **Method (ExpeL / Reflexion-style):**
  1. run `base` on a **DEV** set → collect actual failures (wrong calls, errors, broken deps);
  2. **cluster** the failures (LLM or manual) into recurring failure modes;
  3. **derive** one skill card per cluster;
  4. evaluate `bottom-up-skills` vs `top-down-skills` (E1) vs `base` on **held-out TEST**.
- **Scope (PM's third role):** derive on **PM** (richest error data + covered/uncovered
  structure) as DEV; test on the **other domains + cross-dataset** as held-out TEST. If
  PM-derived skills lift untouched domains → generalization **and** the derived taxonomy
  transfers (answers the "bottom-up doesn't scale" worry empirically).
- **Dev/test discipline (mandatory):** derive on DEV, report on TEST. Deriving and
  reporting on the same set = prompt-level overfitting (leakage, one level up).
- **Success:** bottom-up ≈ or > top-down on held-out TEST; and ≥1 cluster reveals a mode
  not in the §2.1 taxonomy.
- **Cost:** ~$1 + clustering. **Depends:** E1 (top-down baseline) + error-analysis tooling.
  **Type:** strengthening, not critical path.

## Cross-cutting analysis (layer onto any run)
- **Per-failure-mode breakdown (S5):** tag each error by the §2.1 taxonomy; report which
  modes each method reduces. Turns raw accuracy into mechanism.
- **Always report the honesty split** (covered/uncovered or held-out) — never aggregate
  alone.

## The critical path (if you do nothing else)
**E0 ✅ → E0.5 → E1 → (E2 if needed) → E5 → E7.** E0 is done (leakage diagnosed); the live
path starts at E0.5. Everything else (E3 examples, E4 retrieval, E6 multi-model) is
strengthening, not load-bearing, for the core thesis.
