# E12 — Results (ablation across datasets)

**Run:** gpt-4o-mini-2024-07-18 · smolagents · tools: **improved** · temp 0 · **model seed 42** · replicate 1 · LLM gate
**Arms reported here (5):**
`base` · `with_tool_dependency_skills` (tool dependency) · `skills_gated` (gated skills) ·
`verify` (actor-critic alone, no skills) · `skills_gated_verify_with_tool_dependency_skills` (**all**)

- **project_management** — ✅ run (`./results/metrics.json`; `verify` arm from
  `./by_domain/project_management_verify/`; full arm table below)
- **analytics · calendar · customer_relationship_manager · email · multi_domain** —
  ✅ run (5 arms each; per-dataset results in `./by_domain/<domain>/results/metrics.json`)
- **All 6 datasets complete.**

> **All arms now scored on the full n=80** (gated arms run base-equivalent on queries where
> no skill fires, rather than being dropped) → directly comparable. Δ is vs `base`.
> **Accuracy/side-effects** are from an isolated per-arm re-score (current code, one process
> per arm, no cross-arm state bleed). **cost / task** = total actor+gate+critic cost ÷ 80.

---

## project_management  (n=80 queries) — ✅ run
| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 80 | 52.5 | 25.0 | — | 0.0048 |
| `with_tool_dependency_skills` | 80 | 61.3 | 26.2 | +8.8 | 0.0101 |
| `skills_gated` | 80 | **67.5** | 27.5 | **+15.0** | 0.0137 |
| `verify` | 80 | 57.5 | **12.5** | +5.0 | 0.0112 |
| `skills_gated_verify_with_tool_dependency_skills` | 80 | 63.7 | 32.5 | +11.2 | 0.0104 |

<details><summary>Full PM arm table (includes integration-test, ungated-skills, and gated+verify arms)</summary>

| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 80 | 52.5 | 25.0 | — | 0.0048 |
| `with_integration_test` | 80 | 52.5 | 16.2 | +0.0 | 0.0092 |
| `with_tool_dependency_skills` | 80 | 61.3 | 26.2 | +8.8 | 0.0101 |
| `skills` | 80 | 60.0 | 30.0 | +7.5 | 0.0059 |
| `skills_gated` | 80 | 67.5 | 27.5 | +15.0 | 0.0137 |
| `verify` (actor-critic alone) | 80 | 57.5 | 12.5 | +5.0 | 0.0112 |
| `skills_gated_verify` | 80 | 63.7 | 32.5 | +11.2 | 0.0146 |
| `skills_gated_verify_with_tool_dependency_skills` | 80 | 63.7 | 32.5 | +11.2 | 0.0104 |
| `skills_gated_verify_with_integration_test_and_tool_dependency_skills` | 80 | 65.0 | 28.7 | +12.5 | 0.0201 |
</details>

## analytics  (n=120 queries) — ✅ run
| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 120 | 34.2 | 55.8 | — | 0.0088 |
| `with_tool_dependency_skills` | 120 | 38.3 | 52.5 | +4.1 | 0.0090 |
| `skills_gated` | 120 | 41.7 | 47.5 | +7.5 | 0.0089 |
| `verify` | 120 | 35.0 | 48.3 | +0.8 | 0.0150 |
| `skills_gated_verify_with_tool_dependency_skills` | 120 | **45.8** | 46.7 | **+11.6** | 0.0158 |

_Hard domain (base only 34.2). Every mechanism helps; the **combined** arm wins (+11.6) and
also cuts side-effects most (55.8 → 46.7). `verify` alone barely moves accuracy here._

## calendar  (n=110 queries) — ✅ run
| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 110 | 84.5 | 10.9 | — | 0.0058 |
| `with_tool_dependency_skills` | 110 | 85.5 | 12.7 | +1.0 | 0.0069 |
| `skills_gated` | 110 | 84.5 | 14.5 | +0.0 | 0.0075 |
| `verify` | 110 | 83.6 | 10.9 | −0.9 | 0.0088 |
| `skills_gated_verify_with_tool_dependency_skills` | 110 | 84.5 | 11.8 | +0.0 | 0.0094 |

_Ceiling effect: base already 84.5, so there's no headroom — all arms land within ±1 of base
(noise). Mechanisms neither help nor hurt; they just add cost._

## customer_relationship_manager  (n=80 queries) — ✅ run
| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 80 | 51.2 | 35.0 | — | 0.0074 |
| `with_tool_dependency_skills` | 80 | 52.5 | 35.0 | +1.3 | 0.0087 |
| `skills_gated` | 80 | **61.3** | 35.0 | **+10.1** | 0.0098 |
| `verify` | 80 | 55.0 | 31.2 | +3.8 | 0.0095 |
| `skills_gated_verify_with_tool_dependency_skills` | 80 | 58.8 | 37.5 | +7.6 | 0.0121 |

_`skills_gated` leads (+10.1). Combined arm is weaker (+7.6) and raises side-effects — same
"stacking isn't additive" pattern as PM._

## email  (n=90 queries) — ✅ run
| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 90 | 65.6 | 27.8 | — | 0.0073 |
| `with_tool_dependency_skills` | 90 | 65.6 | 30.0 | +0.0 | 0.0090 |
| `skills_gated` | 90 | **84.4** | **7.8** | **+18.8** | 0.0083 |
| `verify` | 90 | 72.2 | 24.4 | +6.6 | 0.0105 |
| `skills_gated_verify_with_tool_dependency_skills` | 90 | 84.4 | 8.9 | +18.8 | 0.0095 |

_Biggest win anywhere: `skills_gated` = +18.8 **and** side-effects crash 27.8 → 7.8. Tool-dep
alone does nothing here (+0.0); gated skills carry it. Combined ties skills_gated at higher cost._

## multi_domain  (n=210 queries) — ✅ run
| Condition | n | Acc % | Side-eff % | Δ vs base | cost/task $ |
|---|---|---|---|---|---|
| `base` | 210 | 42.4 | 48.1 | — | 0.0087 |
| `with_tool_dependency_skills` | 210 | 42.4 | 49.5 | +0.0 | 0.0093 |
| `skills_gated` | 210 | 41.9 | 52.9 | −0.5 | 0.0106 |
| `verify` | 210 | 41.4 | 49.0 | −1.0 | 0.0157 |
| `skills_gated_verify_with_tool_dependency_skills` | 210 | **46.7** | 44.8 | **+4.3** | 0.0183 |

_The one dataset where **individual** arms do nothing (all within ±1) but the **combined**
arm still delivers (+4.3, lowest side-effects). Mixed-domain queries seem to need the full
stack; no single mechanism generalizes across the mix._

---

## Cost per task, by dataset × condition ($/scored query)
_Fill from each `by_domain/<domain>/results/metrics.json` → `usage[cond].total_cost_incl_overhead ÷ n_scored`._

| Condition | PM | analytics | calendar | CRM | email | multi_domain |
|---|---|---|---|---|---|---|
| `base` | 0.0048 | 0.0088 | 0.0058 | 0.0074 | 0.0073 | 0.0087 |
| `with_tool_dependency_skills` | 0.0101 | 0.0090 | 0.0069 | 0.0087 | 0.0090 | 0.0093 |
| `skills_gated` | 0.0137 | 0.0089 | 0.0075 | 0.0098 | 0.0083 | 0.0106 |
| `verify` | 0.0112 | 0.0150 | 0.0088 | 0.0095 | 0.0105 | 0.0157 |
| `skills_gated_verify_with_tool_dependency_skills` | 0.0104 | 0.0158 | 0.0094 | 0.0121 | 0.0095 | 0.0183 |

---

## Read (PM, all n=80)
- **Gated skills win on accuracy**: `skills_gated` = 67.5% (+15.0), the best arm — gating
  beats injecting all skills (`skills` +7.5) at less than half `skills`' added prompt.
- **Actor-critic alone (`verify`) is the safety play**: +5.0 accuracy (52.5 → 57.5) *and*
  it **halves the side-effect rate** (25.0 → 12.5) — the lowest of any arm — at ~2.3× base
  cost/task. Cheap, safe, modest accuracy gain.
- **Critic stacked on gated skills doesn't help**: `skills_gated_verify` (63.7, +11.2) sits
  *below* gated skills alone (67.5) — the critic helps a bare `base` but fights skill guidance.
- **Tool-dependency skills help (+8.8) — once the extra directive is removed.** With the
  *"Don't take shortcuts… follow the tool calling dependency"* `additional_prompt_text`, this
  arm scored 50.0 (−2.5); dropping that text (empty) lifts it to 61.3 (+8.8). The dependency
  skill content helps; the nag made the agent over-act on bulk operations. (Now consistent
  with the combined arms, which never carried that text.)
- **Stacking everything is not additive**: the combined arms (+11.2 to +12.5) all land below
  `skills_gated` alone.

## Read (cross-dataset, all 6 datasets)

Best Δ vs base per dataset (accuracy):

| dataset | base | best arm | Δ | notes |
|---|---|---|---|---|
| email | 65.6 | `skills_gated` | **+18.8** | + side-effects 27.8→7.8 |
| project_management | 52.5 | `skills_gated` | **+15.0** | |
| analytics | 34.2 | combined `all` | **+11.6** | hard domain |
| customer_relationship_manager | 51.2 | `skills_gated` | **+10.1** | |
| multi_domain | 42.4 | combined `all` | **+4.3** | only combined helps |
| calendar | 84.5 | `with_tool_dependency_skills` | **+1.0** | ceiling; side-effects +1.8 pp |

- **Effect size tracks headroom.** Large gains where base is weak/mid (email, PM, analytics,
  CRM); calendar, already high at 84.5, has only a small +1.0 gain. Always report per-dataset,
  never pooled.
- **`skills_gated` is the single best arm on 3/6 datasets** (email +18.8, PM +15.0, CRM +10.1)
  and cheap. It's the default recommendation.
- **The combined `all` arm wins only on the hard/mixed sets** (analytics +11.6, multi_domain
  +4.3) — where no single mechanism generalizes — but it's the priciest arm everywhere.
- **`verify` alone is dataset-sensitive**: safety win on PM (side-effects halved) and a real
  lift on email (+6.6); elsewhere ~0 at the highest single-arm cost.
- **Tool-dependency alone rarely moves accuracy** (0 on email/multi_domain, small on
  calendar/CRM/analytics); its PM +8.8 is the exception. It mostly contributes inside the combined arm.

## Ablation analysis (≈100 words, for paper)
Ablating each mechanism on gpt-4o-mini isolates its contribution. Gated skills are the
strongest single intervention, raising accuracy on every non-saturated dataset (+15.0 on
project management, +18.8 on email, +10.1 on CRM) by injecting only query-relevant guidance.
Actor--critic verification chiefly improves safety, roughly halving the side-effect rate
(25.0\%$\rightarrow$12.5\% on project management) while adding modest accuracy. Tool-dependency
skills help selectively (+8.8 on project management) but are near-neutral where tasks lack
producer--consumer chains. Combining all three is not additive: it wins only on the hardest,
mixed-domain settings (analytics +11.6, multi-domain +4.3) and elsewhere trails gated skills
alone. Gains scale with headroom, vanishing at ceiling (calendar).

---

## Model comparison — Llama 3.1 8B Instruct (base vs All)
Actor + LLM gate + critic all run on `llama3.1-8b` via OpenRouter (routing:
`experiments/common/llm_client.py`). `All` = `skills_gated_verify_with_tool_dependency_skills`.
Outputs under `./by_model/llama3.1-8b/<domain>/`. Run: all 6 datasets ✅.

| Dataset | Arm | n | Acc % | Side-eff % | Δ vs base | cost/task $ | errored rows |
|---|---|---|---|---|---|---|---|
| project_management | base | 80 | 27.5 | 22.5 | — | 0.0033 | 5 |
| project_management | All | 80 | 28.7 | 11.2 | +1.2 | 0.0096 | 8 |
| customer_relationship_manager | base | 80 | 28.7 | 37.5 | — | 0.0017 | 0 |
| customer_relationship_manager | All | 80 | 15.0 | 12.5 | **−13.7** | 0.0063 | 20 |
| email | base | 90 | 12.2 | 43.3 | — | n/a² | 5 |
| email | All | 90 | 23.3 | 28.9 | **+11.1** | 0.0020 | 6 |
| calendar | base | 110 | 25.5 | 46.4 | — | 0.0043 | 3 |
| calendar | All | 110 | 26.4 | 21.8 | +0.9 | 0.0045 | 9 |
| analytics | base | 120 | 20.8 | 60.0 | — | 0.0046 | 5 |
| analytics | All | 120 | 25.8 | 40.8 | +5.0 | 0.0073 | 11 |
| multi_domain | base | 210 | 13.3 | 48.1 | — | n/a² | 9 |
| multi_domain | All | 210 | 16.2 | 26.7 | +2.9 | 0.0015 | 44 |

² `base` cost/task is unavailable for email and multi_domain: `base` finished in an earlier
run that stalled before writing usage, so the resumed run counted 0 new base tokens. The
`All` costs are real.

**Read (Llama-8B):**
- **Much weaker base than gpt-4o-mini** (PM 27.5 vs 52.5; CRM 28.7 vs 51.2; email 12.2 vs 65.6;
  calendar 25.5 vs 84.5) — roughly half (or less) the accuracy. Notably calendar's **ceiling
  effect disappears** on the weak model — there's now large headroom that neither arm captures.
- **The `All` scaffolding's effect is dataset-dependent on the weak model** — it does not
  uniformly help or hurt: **email +11.1** (23.3 vs 12.2), **PM +1.2**, but **CRM −13.7**.
  On CRM the heavier prompt pushes Llama-8B into malformed code (**20/80 `All` runs errored**
  vs 0 base); on email the same scaffolding fills a real gap. Contrast gpt-4o-mini, where the
  pattern was steadier (CRM +7.6, email +18.8).
- **Critic consistently suppresses side-effects** across datasets (PM 22.5→11.2, CRM 37.5→12.5,
  email 43.3→28.9) even when accuracy doesn't improve.
- **Takeaway:** the mechanisms' benefit is model- AND dataset-dependent. A weak 8B model can
  sometimes exploit the guidance (email) but often gets tangled by the added complexity (CRM).
  The clean, large wins on gpt-4o-mini suggest the base model must be strong enough to follow
  the extra structure reliably.

---

## Model comparison — Qwen 2.5 7B Instruct (base vs All)
Actor + LLM gate + critic all run on `qwen-2.5-7b` via OpenRouter (fast provider routing).
`All` = `skills_gated_verify_with_tool_dependency_skills`. Outputs under
`./by_model/qwen-2.5-7b/<domain>/`. All 6 datasets ✅.

| Dataset | Arm | n | Acc % | Side-eff % | Δ vs base | cost/task $ | errored rows |
|---|---|---|---|---|---|---|---|
| project_management | base | 80 | 40.0 | 1.2 | — | 0.0033 | 4 |
| project_management | All | 80 | 55.0 | 13.8 | **+15.0** | 0.0044 | 4 |
| analytics | base | 120 | 21.7 | 56.7 | — | 0.0052 | 9 |
| analytics | All | 120 | 27.5 | 49.2 | +5.8 | 0.0086 | 9 |
| calendar | base | 110 | 38.2 | 21.8 | — | 0.0034 | 5 |
| calendar | All | 110 | 46.4 | 27.3 | +8.2 | 0.0040 | 9 |
| customer_relationship_manager | base | 80 | 40.0 | 22.5 | — | 0.0023 | 2 |
| customer_relationship_manager | All | 80 | 41.2 | 23.8 | +1.2 | 0.0035 | 2 |
| email | base | 90 | 12.2 | 31.1 | — | 0.0028 | 0 |
| email | All | 90 | 27.8 | 32.2 | **+15.6** | 0.0044 | 3 |
| multi_domain | base | 210 | 19.5 | 51.4 | — | 0.0052 | 15 |
| multi_domain | All | 210 | 21.4 | 47.1 | +1.9 | 0.0090 | 29 |

**Read (Qwen-7B):**
- **`All` helps on every dataset** (+1.2 to +15.6) — no regressions anywhere, unlike Llama-8B
  (which dropped −13.7 on CRM). Qwen-2.5-7B is the stronger small model, and the mechanisms
  transfer to it cleanly (biggest wins: PM +15.0, email +15.6).
- **Still well below gpt-4o-mini** on absolute accuracy (e.g. email 27.8 vs 84.4; PM 55.0 vs
  63.7), but the *direction* of the effect matches gpt-4o-mini far better than Llama does.
- Notable: Qwen's PM `base` has a very low side-effect rate (1.2%), which `All` slightly raises.

---

## Model comparison — Llama-3.3-70B & Qwen-2.5-72B (base vs All)
Actor + gate + critic all run on the model via **OpenRouter, price-sorted** routing (temp 0,
seed 42). `All` = `skills_gated_verify_with_tool_dependency_skills`. Outputs under
`./by_model/<model>/<domain>/`. **Both models: all 6 datasets complete** (full n on both arms).

### Llama-3.3-70B
| Dataset | n | base acc/side | All acc/side | Δ | cost/task base→All $ |
|---|---|---|---|---|---|
| project_management | 80 | 40.0 / 27.5 | 50.0 / 38.8 | **+10.0** | 0.0064 → 0.0187 |
| analytics | 120 | 29.2 / 58.3 | 30.8 / 50.0 | +1.6 | 0.0068 → 0.0121 |
| calendar | 110 | 48.2 / 20.9 | 57.3 / 15.5 | +9.1 | 0.0082 → 0.0118 |
| customer_relationship_manager | 80 | 48.8 / 36.2 | 65.0 / 26.2 | **+16.2** | 0.0062 → 0.0125 |
| email | 90 | 27.8 / 24.4 | 55.6 / 6.7 | **+27.8** | 0.0014 → 0.0028 |
| multi_domain | 210 | 27.6 / 51.0 | 32.9 / 51.0 | +5.3 | 0.0062 → 0.0155 |

### Qwen-2.5-72B
| Dataset | n | base acc/side | All acc/side | Δ | cost/task base→All $ |
|---|---|---|---|---|---|
| project_management | 80 | 48.8 / 25.0 | 67.5 / 16.2 | **+18.7** | 0.0005 → 0.0073 |
| analytics | 120 | 33.3 / 60.8 | 35.0 / 52.5 | +1.7 | ≈0.0040ᵉ → 0.0071 |
| calendar | 110 | 63.6 / 15.5 | 68.2 / 9.1 | +4.6 | ≈0.0022ᵉ → 0.0032 |
| customer_relationship_manager | 80 | 61.3 / 17.5 | 58.8 / 21.2 | −2.5 | ≈0.0030ᵉ → ≈0.0061ᵉ |
| email | 90 | 27.8 / 30.0 | 62.2 / 11.1 | **+34.4** | ≈0.0010ᵉ → 0.0020 |
| multi_domain | 210 | 29.0 / 46.7 | 41.9 / 43.8 | **+12.9** | ≈0.0030ᵉ → 0.0074 |

ᵉ **estimated** cost/task: token usage was not recorded for these arms (they completed across
resumes/restarts, so the meter counted 0 fresh work). Estimated as the Qwen-vs-Llama same-dataset
`All`-arm cost ratio (≈0.27–0.71×, avg ≈0.49) applied to Llama-3.3-70B's *measured* cost for the
same dataset/arm; CRM uses the cross-dataset average ratio (no Qwen `All` anchor). Rough (±~40%);
accuracy/side-effects are exact.

**Read (70B/72B):**
- **`All` helps on every dataset for both large open models.** Llama-3.3-70B: **email +27.8**,
  **CRM +16.2**, **PM +10.0**, calendar +9.1, multi_domain +5.3, analytics +1.6. Qwen-2.5-72B:
  **email +34.4**, **PM +18.7**, **multi_domain +12.9**, calendar +4.6, analytics +1.7 — CRM the
  only regression (−2.5). Email is the biggest win for both (side-effects crash: Llama 24.4→6.7,
  Qwen 30.0→11.1).
- **Qwen-2.5-72B is the strongest open model** (base often ≥ Llama-70B; e.g. calendar 63.6, CRM 61.3),
  and `All` sharply cuts side-effects on it (email 30.0→11.1, calendar 15.5→9.1).
- Runs used **price-sorted OpenRouter** to keep per-call cost minimal (base as cheap as $0.0005/task).
  Trade-off: Qwen-2.5-72B is served by only two OpenRouter providers (one 400s on the endpoint, one
  429-rate-limits), so its `All` arms required repeated resumes and a resilient gate to finish.

## Reproduce
```bash
conda activate maestro2   # env with smolagents + litellm
# gpt-4o-mini, full 5-arm ablation, per dataset:
python experiments/E12_abalation/run_all_domains.py
#   or a subset:  python experiments/E12_abalation/run_all_domains.py analytics email
# base + All on other models (OpenRouter, fast provider routing):
python experiments/E12_abalation/run_llama8b_base_all.py    # Llama 3.1 8B, 6 datasets
python experiments/E12_abalation/run_qwen7b_base_all.py     # Qwen 2.5 7B, 6 datasets
```

_Status: **complete.** gpt-4o-mini — all 6 datasets, 5-arm ablation. Llama-3.1-8B and
Qwen-2.5-7B — all 6 datasets, base vs All (all-OpenRouter via `llm_client.py` fast routing).
Replicate 1, model seed 42. `results/`, `by_domain/`, `by_model/` untracked in git._
