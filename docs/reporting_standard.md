# Reporting Standard

How every experiment (E0–E7) reports results, so runs are comparable and re-poolable.
Consumed by `experiments/common/scoring.py`; linked from
[../experiments/README.md](../experiments/README.md).

---

## 1. Core rule
> Store results **tidy (one row per cell)**; pivot for display.
> Always report the **split** (seen/unseen), the **condition**, and **n** — never
> aggregate accuracy alone.

## 2. Vocabulary (do not conflate)
- **Experiment** = the study / question (E0, E1, …). The folder.
- **Condition** = the treatment arm compared *inside* an experiment (`base`, `improved`,
  `skills`, `clean-examples`, `k=3`, …). `base` is the shared control; `improved` is the
  current method (rewritten descriptions + integration tests). Both are fixed, shared
  builders in `experiments/common/conditions.py` — they mean the same thing in every
  experiment.
- **Split** = seen vs unseen — the leakage / generalization axis.
- **Grain** = *what* is seen/unseen (see §4). Must be stated per table.

## 3. Tidy schema (one row per cell)
```
experiment, model, seed, condition, domain, split_grain, split, n, accuracy, side_effect_rate, delta_vs_base
```
- `accuracy` — % correct (repo `is_correct`, outcome-based).
- `side_effect_rate` — % wrong-with-unwanted-side-effects (repo `has_side_effects`).
  **Mandatory** — this is a tool-*hallucination* paper; harmful wrong actions matter.
- `delta_vs_base` — `accuracy(condition) − accuracy(base)` for the same (domain, split).
- `n` — cell count. **Mandatory** (the "+3.3 = 1 query" trap).

## 4. Split grains (state which one each table uses)
Maps to the generalization ladder (retrieval_design §10):

| Grain | "seen" = | "unseen" = | Used in |
|---|---|---|---|
| **template** | covered PM templates (5) | uncovered PM templates (3) | E0, E1 (PM) |
| **tool** | tools with an example | tools without | E3 |
| **domain** | domains the method touched | untouched domains | E1, E5 |
| **dataset** | WorkBench | API-Bank | E7 |

Every display table header states: **model · #seeds · split grain**.

## 5. Fairness rules (which conditions are comparable where)

### 5.1 Two claims, two fair comparisons
- **Mechanism (head-to-head):** "skills teach tool-use as well as / better than tests."
  Fair **only where both conditions are applied** → currently **PM only**. Compare
  `skills` vs `improved` vs `base`.
- **Generalization / scalability:** "skills help domains with no examples; the test method
  can't reach them." On untouched domains compare **`skills` vs `base`** — *never*
  `skills` vs `improved` (improved is absent there, so a win is trivial and misleading).

### 5.2 `improved` is not constant across domains — never pool it
`improved` = rewritten descriptions **+** integration tests **only on PM**. On other
domains it is descriptions-only (and analytics uses *base* descriptions). So:
- **Report `improved` per-domain, never as one pooled number.**
- Label what `improved` contains in each domain (desc+tests vs desc-only).

### 5.3 Applicability matrix (what to compare per domain)

| Domain | base | improved | skills | Fair comparison |
|---|---|---|---|---|
| PM | ✓ | ✓ (desc+tests) | ✓ | skills vs improved vs base (head-to-head) |
| Email / Calendar / Analytics / CRM | ✓ | ~ (desc-only) | ✓ | **skills vs base** (generalization) |

Do **not** headline "skills beat improved" in a domain where `improved` has no tests.

## 6. Canonical display table (pivot of §3)
Header e.g.: **E1 · gpt-4o-mini · 3 seeds · grain: template (PM), domain (others)**

| condition | domain | split (grain) | n | acc % | Δ base | side-eff % |
|---|---|---|---|---|---|---|
| base | PM | unseen (template) | 30 | 43.3 | — | 6.7 |
| improved | PM | unseen (template) | 30 | 46.7 | +3.3 | 6.7 |
| skills | PM | unseen (template) | 30 | 55.0 | +11.7 | 3.3 |
| base | calendar | all (domain) | 40 | 52.0 | — | 5.0 |
| skills | calendar | unseen (domain) | 40 | 61.0 | +9.0 | 2.5 |

- The **headline number** is the delta on the **unseen** split.
- Once ≥2 seeds exist, append **± sd** to accuracy and mark significance (S2).

## 7. Cost / tokens / latency (auto-recorded)
The shared runner captures, per condition, into `metrics.json` under `usage`:
`prompt_tokens, completion_tokens, total_tokens, cost_usd, wall_seconds, sec_per_query`.
Tokens come from LangChain's OpenAI callback; cost from `experiments/common/pricing.py`
(update prices there). Each experiment's `RESULTS.md` includes a **Cost, tokens & latency**
table. This is the reliable per-experiment cost — *not* admin-spend before/after (the Costs
API is daily-bucketed and lags, so it can't isolate one run).

## 8. Minimum every experiment must report
1. Tidy records (§3) → `results/metrics.json` + `results/raw/*.csv`.
2. The canonical table (§6) in the experiment `README.md`/`RESULTS.md`.
3. The **unseen-split delta vs base** stated in the Conclusion.
4. `improved` (if run) broken out **per domain**, never pooled.
5. The **cost/tokens/latency** table (§7).
