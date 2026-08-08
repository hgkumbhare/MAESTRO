# Experiment log — how we got from E0 to E1.11

One place that states **every** experiment in the line, **what it tested**, **whether we actually
ran it**, and the **decision** that led to the next one. Not every planned experiment was run — the
plan branched, and we followed the branch that kept the method *leakage-safe and general*.

**Reading the numbers.** Accuracy = outcome-based (execute predicted tool calls, diff DB state vs
gold), % over the stated queries. SE = side-effect rate (wrong answer *with* a harmful write). All
runs: gpt-4o-mini, smolagents, temp 0 + seed 42 unless noted. **Tool set matters:** E0–E1.6 use the
*original* tool descriptions; **from E1.7 on we switched to the `improved` tool set** (team-standard,
no integration tests) — so the baseline jumps at E1.7 and cross-tool-set comparisons aren't apples-to-apples.

---

## Master table

| ID | Name | What it tested | Status | Headline |
|---|---|---|---|---|
| **E0** | Baselines (PM) | base vs `improved` (rewritten tools **+ integration tests**), PM only, split by whether the eval template was *covered* by a test | ✅ ran | base 38.8 → improved 55.0 (all). **Leakage smoking gun:** covered **+24.0**, uncovered **+3.3** |
| **E0.5** | Harness sanity | diagnostic: does the harness score at all across domains? | ⚠️ partial/diagnostic | template mostly unfilled; separately, an ad-hoc check at E1.7 setup found our runner ≡ repo `generate_results` (10/10 identical) |
| **E1** | Skills, always-on | leakage-safe skill cards injected on *every* query, all 6 domains | ✅ ran | base 44.9 → skills **47.4** (+2.5); SE 40.0→40.0 |
| **E1.5** | Skills, embedding-gated | inject only skills whose *embedding* trigger fires per query | ⚠️ explored, superseded | embedding gate too blunt (missed e.g. delete→fetch) → motivated the LLM gate |
| **E1.5.5** | Skills, LLM-gated | one classifier call picks applicable skills per query (no threshold to tune) | ✅ ran | base 44.9 → skills_gated **48.7** (+3.8); SE 40.0→**36.2** |
| **E1.6** | + parameter-completeness card | add an 8th card (fill required filters e.g. `list_name`) | ⚠️ setup/scratch | folded into E1.7 (the 8-card set + improved tools) |
| **E1.7** | **Improved tools + LLM-gated skills** | the definitive, team-comparable run: improved tools (no leaky tests) × gated 8-card skills | ✅ **ran — DEFINITIVE** | base 50.6 → skills_gated **58.1 (+7.5)**; SE 38.1→**35.2**. Non-empty-gold tasks **+11.2** |
| **E1.8** | Actor-critic verify-and-correct | critic reads task+trace (never gold) → re-invokes actor with feedback, ≤2 iters, on top of gated skills | ✅ ran — **split verdict** | **Real tasks: 57.0 (+12.6 vs base, best condition).** Aggregate 57.5 (< gated 58.1): critic's "found nothing→retry" backfires on empty-gold (−12) while helping real tasks (+8). Motivated the fix ↓ |
| **E1.8b** | Verify + empty-gold-aware critic | same mechanism; critic no longer treats "found nothing" as failure (4 ordered checks) | ✅ ran — **best condition** | **60.4 (+9.8 vs base), non-empty 57.7 (+13.3), lowest SE 32.5.** Critic net −4 → **+16**; empty-gold −12 → +4. Cost: gated $0.0142/correct (cheapest), verify $0.0201/correct (max acc, ~1.5× cost) |
| **E1.9** | Multi-model | does the gated-skills lift hold across models (gpt-4o, llama-3.3-70b, qwen-2.5-72b)? | 🟡 built, not run | runnable now; gpt-4o-mini anchor seeded from E1.7 |
| **E1.10** | Cross-dataset × models | apply the *unchanged* method zero-shot to **API-Bank** (leakage-proof generalization) | 🧩 scaffold | needs API-Bank env adapter; design + stub in place |
| **E1.11** | Tool dependency graph | explicit producer→consumer graph (from tool signatures) as structure, vs prose skills | 🧩 scaffold | `graph.py` skeleton builds a real graph; conditions not yet wired |

**Legend.** ✅ ran · ⚠️ ran but superseded/scratch · 🔄 running · 🟡 built & runnable, not yet run · 🧩 scaffold (design + skeleton).

---

## Planned but NOT run (the branches we didn't take, and why)

These were scaffolded during planning (their `RESULTS.md` are templates with `·` placeholders). We
dropped or deferred each for a reason — recorded here so nothing looks silently abandoned.

| ID | Name | Why not run |
|---|---|---|
| **E2** | Skills + micro-demo grounding | Deprioritized — *gating* (E1.5.5) gave the bigger, cleaner win than grounding each card with a demo. Revisit only if a card misfires. |
| **E3** | Example bank | Retrieving worked *examples* risks re-introducing the E0 leakage (examples resemble eval templates). We chose dataset-agnostic **skills** over examples. |
| **E4** | Example retrieval | Same leakage concern as E3 — it's example-retrieval, not skill-retrieval. Superseded by the LLM *skill* gate. |
| **E5** | All-domains rollout | Folded in — from E1.5 onward *every* run is all-6-domains, so a separate rollout was redundant. |
| **E7** | Cross-dataset (API-Bank) | **Reborn as E1.10** (now crossed with multi-model). |
| **E8** | Bottom-up skill derivation | Deferred — auto-deriving skills from clustered failures is the scalability story; a future step after the transfer results (E1.9/E1.10) land. |

---

## The narrative — how each result forced the next step

1. **E0 exposed leakage.** The `improved` method's gain was **+24 on templates a test covered** but
   only **+3.3 on uncovered** ones → it was *memorizing eval templates*, not learning tool use. That
   killed integration tests as the mechanism and set the honesty bar: **any method must be
   leakage-safe** (derived from tool semantics, never eval answers).

2. **E1 replaced leakage with skills.** Dataset-agnostic skill cards (identifier-resolution,
   fetch-before-act, …) — always-on. Real but small (+2.5): always-on skills add noise on queries
   they don't apply to.

3. **E1.5 → E1.5.5 gated the skills.** Inject only the relevant cards per query. Embedding triggers
   (E1.5) were too blunt; an **LLM classifier** (E1.5.5) judged applicability better and — crucially —
   **has no threshold to tune**, so there's no eval-tuning leakage. +3.8 acc *and* SE 40→36.

4. **E1.6 → E1.7 fixed the biggest failure mode + matched the team.** Error analysis showed the
   agent dropping required filters → added a **parameter-completeness** card (E1.6). Then switched to
   the team-standard **improved tools (no leaky tests)** for comparability. Result (E1.7): the
   definitive **+7.5 overall, +11.2 on real (non-empty-gold) tasks, SE down**.

5. **E1.8 stopped playing whack-a-mole — and revealed the artifact biting the mechanism.** Instead of
   more per-failure cards, a **general verify-and-correct mechanism**: a critic reads the task + the
   agent's own trace (never the gold) and, if incomplete, re-invokes the agent with one specific fix.
   Result was a **split verdict**: best condition on real tasks (**57.0, +12.6 vs base**) but *below*
   plain gated on aggregate (57.5 vs 58.1). Cause: the v1 critic's "found nothing → broaden and retry"
   heuristic is right on real tasks (**+8**) but converts correct-by-inaction into wrong-by-action on
   **empty-gold** tasks (**−12**) — the empty-gold artifact striking the critic itself. **E1.8b** fixes
   it with an empty-gold-aware critic (4 ordered checks; smoke 6/6) — recover the −12, keep the +8.

6. **E1.9 / E1.10 / E1.11 attack generalization, not more mechanisms.** The open reviewer questions
   are "only one model?" (→ **E1.9 multi-model**) and "only WorkBench?" (→ **E1.10 cross-dataset to
   API-Bank**, leakage-proof because the method never saw it). **E1.11** makes the paper's original
   thesis — *tools as a dependency graph* — explicit and structural, and asks whether that beats or
   complements prose skills.

---

## Caveats carried forward

- **Empty-gold artifact.** Some WorkBench tasks have gold = "do nothing"; a base agent that fails to
  act scores *correct*, while a more capable agent that acts can be penalized. So **aggregate accuracy
  under-credits the method** — always report the **non-empty-gold split** (where E1.7 is +11.2, vs
  +7.5 aggregate).
- **Tool-set break at E1.7.** Don't compare original-tools numbers (E0–E1.6) head-to-head with
  improved-tools numbers (E1.7+). Within each regime the base→treatment deltas are the honest signal.

---

*Next:* E1.8 completes → report base vs gated vs verify (+ critic reliability). Then E1.9 is a
one-command run; E1.10/E1.11 need the adapter/condition wiring noted in their READMEs.
