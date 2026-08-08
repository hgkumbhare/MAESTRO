# MAESTRO Paper — Review & Revision Tracker

Working document for revising *"Reduce Tool Interaction Hallucinations in LLMs"*
(Kumbhare & Madisetti). Issues are ranked by how much they threaten acceptance.
We work through them one at a time; update **Status** as we go.

**Status legend:** ⬜ Not started · 🟡 In progress · ✅ Resolved · ⏸️ Parked / deferred

---

## Current system — what is happening right now

Reconstructed from the code (`scripts/inference/generate_results.py` →
`src/evals/utils.py`). This is the pipeline as it actually runs today.

```
                        scripts/inference/generate_results.py
        --model_name  --queries_path  --tool_set {original|improved}
        --agent_engine {langchain|smolagents}  --include_integration_tests
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │  1. LOAD QUERIES        pd.read_csv(queries_path)          │
        │     e.g. "Delete my first meeting on December 13"          │
        └──────────────────────────────────────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │  2. BUILD TOOLKIT    get_toolkits(tool_set=...)            │
        │                                                            │
        │   tool_set = 'original'  → base tool descriptions          │
        │   tool_set = 'improved'  → hand-rewritten descriptions     │
        │   +include_integration_tests →                             │
        │        apply_integration_test_documentation(tools)         │
        │        ↳ APPENDS integration-test source code into each    │
        │          tool's `.description` string                      │
        │                                                            │
        │   ***THIS TEXT IS THE ONLY THING THAT CHANGES between      │
        │      Base and Improved. Everything below is identical.***  │
        └──────────────────────────────────────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │  3. PER-QUERY LOOP                                         │
        │     ├─ reset_all()          restore sandbox DBs to default │
        │     ├─ build ReAct agent    (langchain STRUCTURED_CHAT_    │
        │     │     ZERO_SHOT_REACT)  tools carry the descriptions   │
        │     │     from step 2; max_iterations=20, timeout=120s     │
        │     └─ agent.run(system_prompt + query)                    │
        │           ┌───────── ReAct loop ─────────┐                 │
        │           │  think → act(tool call) →     │                │
        │           │  observe(DB result) → repeat  │                │
        │           └───────────────────────────────┘                │
        │        collect predicted function_calls                    │
        └──────────────────────────────────────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────────┐
        │  4. EVALUATE   calculate_metrics(ground_truth, results)    │
        │     compare predicted function_calls vs ground-truth calls │
        │     → Accuracy + side-effect categories                    │
        └──────────────────────────────────────────────────────────┘
```

**The key takeaway (feeds C2/C3):** the entire "MAESTRO method" is a change to the
**text of the tool descriptions** (integration-test examples injected as in-context
demonstrations). There is no runtime validation, no execution of the tests, no
corrective feedback loop — despite what the abstract describes.

### Code-level observations found while tracing the pipeline
- `INTEGRATION_TESTS = {}` in `integration_test_doc_utils.py` is **empty**; tests are
  read from `tests/src/tools_improved_smolagents/test_integration_tests.py` at
  runtime. Confirm that file is populated for the runs that produced Table 2.
- **Debug `print()` statements left in** production path ("congrats added integration
  tests…", "Ohh no failed…"). Cosmetic, but signals unfinished code. → see P2.
- **Inconsistent temperature:** langchain path uses `temperature=0`, smolagents path
  uses `temperature=0.7`. This undermines reproducibility and cross-engine
  comparison. → feeds S2.
- **Improved toolkit does NOT swap analytics:** the `improved` branch uses the *base*
  `analytics_toolkit` (not an improved version). Worth checking against the
  Analytics = 0% result. → feeds C1.

### Zoom-in: how the integration-test documentation is created & injected

There are **two stages**, and they are easy to conflate:

**Stage A — Authoring the tests (manual / offline; NOT in the code path).**
The integration tests are hand-written pytest functions in
`tests/src/tools_improved_smolagents/test_integration_tests.py` (currently 5, all
project-management). The prompt on **p.8 of the paper** ("Create 5–10 new integration
tests… Output only the Python integration tests") is the *intended* LLM recipe for
producing them — but it is **not wired into the pipeline**. Test creation is an
offline/manual step; the code only consumes existing test files.

**Stage B — Injecting them into the prompt** (`src/evals/integration_test_doc_utils.py`,
function `apply_integration_test_documentation(tools)`), run at toolkit-build time:

```
test_integration_tests.py
        │
        ▼
1. Read file source, AST-parse it
   _get_test_source_by_name()  → {test_name: full source text of `def test_*`}
        │
        ▼
2. For each test, find which tools it calls
   _extract_tool_calls_from_test(): walks the AST, grabs every `X.attr`
   attribute access → treats `attr` as a tool name
   e.g.  project_management.search_tasks  →  "search_tasks"
        │
        ▼
3. Build mapping   {tool_name: [test_source, ...]}
        │
        ▼
4. For each tool in the toolkit:
     if tool.name ∈ mapping:
         tool.description +=
             "\n\nBehavior verified by integration tests:\n\n"
             + ```python <full test function source> ```
     else:
         (unchanged — no examples added)
```

So the injected "documentation" is the **verbatim source of every test function that
mentions that tool**, wrapped in a python code block and appended to the tool's
description string. That augmented description is what the ReAct agent reads.

**Problems with this mechanism (feed C2, C3, S3, P2):**
1. **Coverage is name-matched to the PM tests only** — step 4 augments a tool only if
   its name appears in the mapping. All 5 tests are PM, so only PM tools are treated.
   This is the mechanical cause of the untreated-domain pattern in Table 2. → C1/C4.
2. **Whole test body dumped verbatim** — including `set_tasks(...)` setup,
   `call_tool(...)` helpers, and `assert` statements. The model sees pytest scaffolding
   and assertions, not a clean "call these tools in this order" demonstration. Noisy
   in-context signal.
3. **Tool-call extraction over-collects** — `_extract_tool_calls_from_test` treats
   *every* `Name.attr` as a tool name (`records.append`, `datetime.now`, …). Works
   only because spurious names rarely collide with real tool names; fragile.
4. **"Integration test" is a misnomer for what's used** — nothing is executed or
   verified at inference. Test *source text* is used as few-shot examples. The
   abstract's "integration-test-based supervision / validate tool calls against
   executable specifications" overstates this. → C2.
5. **Dead code + debug noise** — `INTEGRATION_TESTS = {}` is unused; `print()` dumps of
   full tool descriptions run on every inference. → P2.

---

## Tier 1 — Critical (block acceptance as written)

### C1. Reported results contradict the central claim
- **Status:** ⬜
- **Problem:** Table 2 (WorkBench) shows GPT-4o-mini at **0% on Emails, Analytics,
  Multi, and Calendar** for *both* Base and Improved. Only PM (47.5→60) and
  CRM (48.75→72.5) move. The paper claims the method "significantly improves
  tool-call accuracy," but it does nothing in 4 of 6 domains.
- **Evidence it's likely a harness bug, not a real result:** A single Calendar
  query run through this repo's inference + eval scored **100%** — directly
  contradicting "Calendar 0%." So the reported 0%s probably come from a broken
  eval path (generation error, DB state reset, or answer-matching), not true model
  failure.
- **Why it matters:** The empirical contribution collapses if 4/6 domains are
  invalid; and if the 0%s are a bug, fixing it may *strengthen* the results.
- **Proposed action:** Run gpt-4o-mini on a small sample from emails / analytics /
  calendar through the eval harness and trace where it breaks:
  generation vs. answer-matching vs. DB reset.
- **Notes:**

### C2. Method framing ≠ what is implemented
- **Status:** ⬜
- **Problem:** Abstract/intro promise a *system-level* mechanism: "proactively
  validate tool calls against executable specifications," "early detection,"
  "corrective feedback that reduces propagation across multi-step interactions."
  The actual method (Sec. 4 + prompt on p.8) is: **append 5–10 LLM-generated
  integration-test examples to the prompt** — static few-shot prompting. No runtime
  validation, no execution, no feedback loop.
- **Why it matters:** Reviewers will flag overclaiming; the described system does
  not exist in the implementation.
- **Proposed action (pick one):**
  - (a) Rewrite framing honestly: "structured in-context demonstrations of tool
    dependencies," OR
  - (b) Actually build the validation/feedback loop the abstract describes.
- **Notes:**

### C3. No baseline isolating the *cause* of improvement
- **Status:** ⬜
- **Problem:** Improved = Base + extra examples + more tokens. No control for
  "it's just more few-shot examples / more tokens."
- **Why it matters:** Cannot attribute gains to *tool-interaction knowledge*
  without an ablation.
- **Proposed action:** Add a control condition: same number of *generic* examples
  **without** dependency structure. Compare Base vs. Generic-examples vs.
  Integration-tests.
- **Notes:**

### C4. The core hypothesis is never tested (generalization to unseen APIs)
- **Status:** ⬜
- **Problem:** Paper poses the open question — do behavioral examples generalize to
  *unseen* APIs better than descriptions? — but evaluates on the *same* tools the
  integration tests cover.
- **Why it matters:** Generalization to held-out tools is the stated contribution
  and is currently unmeasured. And you cannot distinguish "improved because covered"
  from "improved because generalized" while treated tools are the only ones improving.
- **Quantified coverage gap (2026-07-02):** The 5 tests reference only **3 real tools**
  — `search_tasks`, `update_task` (project_management) and `find_email_address`
  (company_directory). WorkBench has **~26 tools / 5 domains** → **~12% tool coverage**,
  2 domains. (The other names extracted — `atlas.com`, `sys.modules`,
  `importlib.import_module`, etc. — are parser noise, see S3/obs. #3.) 5–10 tests
  fundamentally cannot cover all tools; for API-Bank (2,138 APIs) per-tool coverage is
  hopeless. This makes the *generalization* claim the only viable one — and it must be
  tested directly.
- **Proposed action:** Hold out a subset of tools/domains from the integration-test
  set; measure improvement on those held-out tools specifically. Report per-tool
  coverage explicitly in the paper.
- **Notes:**

---

## Tier 2 — Serious (weaken the paper substantially)

### S1. Only one small model tested
- **Status:** ⬜
- **Problem:** Claims "adaptable to any model" but tests only GPT-4o-mini.
- **Action:** Run ≥2–3 models the repo already supports (gpt-4o,
  llama-3.3-70b, qwen-2.5-72b/7b). Report per-model deltas.
- **Notes:**

### S2. No variance / significance
- **Status:** ⬜
- **Problem:** Single seed, small n. 47.5→60 (PM) may be noise.
- **Action:** Multiple seeds; report mean ± CI; significance test on deltas.
- **Notes:**

### S3. Contamination / leakage — CONFIRMED (procedure/template leakage)
- **Status:** 🟡 (confirmed; needs the covered-vs-uncovered experiment)
- **Problem:** The integration tests demonstrate the gold solution for the **same task
  templates the eval grades on.** PM eval = 8 templates × 10 = 80 queries. **5 of the 8
  templates have a matching integration test** that spells out the exact tool
  selection, sequence, and parameter fields:
  - move-in-progress→in-review, move-overdue-backlog→in-progress,
    move-in-review→completed, reassign-in-progress (sick), move-unfinished→backlog.
  - **Uncovered (3):** add-task-to-backlog, give-overdue-unstarted, take-most-urgent.
  - **Entity overlap too:** test #1 uses "Aisha" (eval has an Aisha query); test #4
    reassigns "Yuki→Carlos" and **Yuki is a real eval entity** (task_id 00000091).
- **Nuance:** Not raw answer-string leakage (tests use synthetic `set_tasks()` records
  with different task_ids), but **procedure/template leakage** — teaching to the test
  distribution. Enough to explain the PM gain (47.5→60) as memorized in-distribution
  solutions rather than transferable skill. Compounds C3 and C4.
- **Built-in control / action:** Split PM results by **covered (5)** vs **uncovered (3)**
  templates. If gains concentrate on covered templates → leakage/memorization. If
  uncovered templates also improve → real generalization (defensible C4 claim).
  Runnable on existing data.
- **RESULT (2026-07-02, gpt-4o-mini, 80 PM queries, base vs improved+tests):**

  | group | n | base% | improved% | delta |
  |---|---|---|---|---|
  | covered (5 templates) | 50 | 36.0 | 60.0 | **+24.0** |
  | uncovered (3 templates) | 30 | 43.3 | 46.7 | **+3.3** (≈1 query, noise) |
  | all | 80 | 38.8 | 55.0 | +16.3 |

  **Conclusion: LEAKAGE CONFIRMED.** Gain is ~7× larger on covered templates; uncovered
  movement is within noise. The method memorizes in-distribution solutions and does not
  generalize. Directly undercuts C4 and reframes the aggregate gain as leakage.
  Harness: `scripts/inference/leakage_experiment.py`; per-query CSVs in scratchpad.
- **Notes:** "improved" here = rewritten descriptions + integration tests combined; even
  so, only covered templates move.

### S4. Table 1 misattributes API-Bank as "ours"
- **Status:** ⬜
- **Problem:** Row "API-Bank (ours) — 1,000 domains / 2,138 APIs." API-Bank is prior
  work [6]; the table appears lifted from that paper.
- **Why it matters:** Research-integrity red flag.
- **Action:** Fix attribution / remove "(ours)" / cite source of the table.
- **Notes:**

### S5. Error analysis not tied to the taxonomy
- **Status:** ⬜
- **Problem:** Rich taxonomy (selection / calling / result hallucinations) defined,
  but results don't measure *which* error types the method reduces. MAESTRO's
  side-effect categories in code could support this.
- **Action:** Break down errors by taxonomy category, before vs. after.
- **Notes:**

### S6. Method's own cost tradeoff unaddressed
- **Status:** ⬜
- **Problem:** Paper criticizes large prompts as "expensive," but the method inflates
  the prompt with integration tests.
- **Action:** Report added token cost; discuss the accuracy/cost tradeoff.
- **Notes:**

---

## Tier 3 — Polish (draft-quality signals; quick fixes)

### P1. Keywords copy-pasted from an unrelated paper
- **Status:** ⬜
- Keywords list "sycophancy mitigation, activation steering, contrastive activation
  addition, representation engineering, TruthfulQA" — none relate to tool use.
  Replace with tool-hallucination terms.

### P2. Structural placeholders / incomplete sections
- **Status:** ⬜
- Empty **Conclusion (Sec. 6)**; dangling headers ("Practical implications.",
  "Domain of the datasets.", "Reproducibility."); literal **"TODO: MAESTRO work"**;
  `:contentReference[oaicite:0]` artifact in ref [17].

### P3. Grammar / prose
- **Status:** ⬜
- e.g., "complex multi-step complex tasks"; run-ons; sentence fragments.
  Full copyedit pass before submission.

---

## Working log
- 2026-07-02 — Created tracker. Confirmed a single Calendar query scores 100% via the
  repo's inference+eval, contradicting the reported "Calendar 0%" (see C1).
- 2026-07-03 — **E1.7 COMPLETE — strongest result (improved-tools baseline, temp0+seed42).** On the
  team-comparable improved-tools base, gated skills (v3, +parameter-completeness) give **overall
  50.6→58.1 (+7.5)**; **non-empty/real-task 44.4→55.6 (+11.2)** — bigger than E1.5.5's +3.8 on the
  weaker original base. **Every domain improves in accuracy** (email +24.4, CRM +12.5, PM +8.7 —
  PM now HELPS, no regression). Side effects overall −2.9; gated fixed 33% (87/263) of base's harmful
  actions, net −20. Baseline finding: improved tools >> original (base 44.9→50.6; PM 38.8→61.3).
  Empty-gold (S7) still drags aggregate (−9.8). Honest headline: **+11.2 acc / −5.6 se on real tasks.**
- 2026-07-03 — **PM regression DIAGNOSED → benchmark artifact (major finding).** Splitting PM by
  gold: on **non-empty (real-task) queries gated BEATS base (34 vs 27, +7)** — skills help. The −2.5
  aggregate is entirely the **21/80 empty-gold queries**: base guesses wrong emails → finds nothing
  → does nothing → matches empty gold ("correct by failing"); gated correctly resolves the email →
  finds the person → acts → wrong when answer is "do nothing" (+ side effects). So WorkBench
  aggregate accuracy **rewards failure-to-resolve-identifiers** and penalizes capability on
  empty-gold queries — likely deflates skills' value across ALL domains. Honest metric = accuracy on
  non-empty gold. Follow-up: re-report all domains split by empty/non-empty gold. → new issue S7.
- 2026-07-03 — **E1.5.5 COMPLETE (LLM-gated skills).** Overall base 44.9 → always-on skills 47.4
  → **gated 48.7** (best). Gating **fixed the flat-domain regressions** (analytics 37.5→40.0=base,
  CRM 37.5→40.0≈base) as the E1 diagnosis predicted, and improved email (→60.0) + multi. **But
  regressed PM** (38.8→36.2, −2.5) — a surprise, since PM is chain-heavy (always-on gave PM +6.2).
  Net: gating is best method so far but trades a PM gain for flat-domain fixes. Sharpened triggers +
  fixed LLM-gate output format (was returning list numbers). See E1_5_5 RESULTS.md.
- 2026-07-02 — **E1 regression diagnosis + cost bug fix.** CRM/analytics regressions (19: 14
  analytics, 5 CRM) are **parameterization noise** — skills add/drop filter args on *single-tool
  query* calls (opposite directions = noise not bias). Root cause: skill cards target multi-step
  dependency chains, irrelevant to flat query tasks → always-on injection perturbs them. Fix =
  **trigger-gated skill injection** (inject a skill only when its `Trigger` matches; cards already
  have Trigger fields — E1 ignored them). This is a SKILLS refinement / E1 follow-up, NOT E4 (E4 =
  example-bank retrieval, a different unit). Also fixed the litellm token bug. See E1 RESULTS.md.
- 2026-07-02 — **E1 COMPLETE (base vs skills, all domains, smolagents, temp 0).** Overall
  base 44.9% → skills 47.4% (**+2.5 acc**); side-effects ~flat (~40%). **Mixed per domain:**
  calendar +12.7, PM +6.2, email +3.3 (email se −10); but CRM −3.7, analytics −2.5 (se worse).
  → current top-down hand-written skills give a small, inconsistent lift, not a uniform win.
  Likely cause: skills phrased as tool-calling rules don't fit smolagents' code-agent paradigm.
  Motivates E2 (grounding) + E8 (bottom-up derivation). Full table: E1 RESULTS.md.
- 2026-07-02 — **C1 essentially RESOLVED (base run, all domains).** smolagents base,
  gpt-4o-mini, temp 0, 690 queries: per-domain accuracy calendar 71.8, email 48.9, CRM 41.2,
  analytics 40.0, PM 38.8, multi 35.7 (overall 44.9%). All domains score **non-zero** →
  the paper's Table 2 "0% for Email/Analytics/Calendar/Multi" was **spurious**, not a real
  harness limitation. No E0.5 debugging needed. Also: base side-effect rates are high
  (20–53%) → the key target for skills to reduce. See `experiments/E1_skills_all/RESULTS.md`.
- 2026-07-02 — **E1 PM pilot (skills).** base vs skills, 80 PM queries, gpt-4o-mini.
  covered 36.0→44.0 (+8.0), uncovered 40.0→43.3 (+3.3). Balanced lift = **no leakage
  signature** (contrast improved's +24/+3.3); side-effects 6.7%→0% on uncovered. Small,
  PM-underpowered → all-domains run is the decisive test. Note base-uncovered 40.0 here vs
  43.3 earlier = ReAct variance (need repeats, S2). See `experiments/E1_skills_all/`.
- 2026-07-02 — **LEAKAGE CONFIRMED (experiment).** gpt-4o-mini on 80 PM queries,
  base vs improved+tests. Covered templates: 36.0→60.0 (+24.0). Uncovered: 43.3→46.7
  (+3.3, ≈1 query = noise). The improvement is concentrated on the 5 templates that have
  matching integration tests; the 3 untested templates barely move. → the "gain" is
  memorization of in-distribution solutions, not generalization. Undercuts C4; confirms
  S3. See `scripts/inference/leakage_experiment.py`.
- 2026-07-02 — **Key finding:** the integration-test suite
  (`tests/src/tools_improved_smolagents/test_integration_tests.py`) has 5 tests, all
  passing — but **all 5 cover only the project-management (tasks) domain.** So the
  "improved" method currently provides behavioral examples for **one domain only**.
  Likely explains Table 2: PM improves (47.5→60) because it is the only treated
  domain; emails/analytics/calendar/multi stay flat because they receive no
  integration tests. CRM's jump (48.75→72.5) likely comes from the hand-rewritten
  `improved` descriptions, not the tests. → strongly informs C1, C3, C4.
  (Note: earlier "0 tests collected" was a malformed pytest command, not a real bug.)
