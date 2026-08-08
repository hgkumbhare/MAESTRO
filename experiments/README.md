# MAESTRO Experiments

> 📌 **New here? Start with [../docs/start_here/](../docs/start_here/)** — the system guide
> (how to run/read experiments, backup/sharding/actor-critic, where keys + constants live), the full
> experiment log (E0→E1.11), and the prompt structure.

Self-contained experiment folders (one per roadmap step) plus shared code in `common/`.
Roadmap & rationale: [../docs/experiment_plan.md](../docs/experiment_plan.md).
Design: [../docs/retrieval_design.md](../docs/retrieval_design.md).
Issue tracker: [../docs/paper_review.md](../docs/paper_review.md).
**Reporting standard: [../docs/reporting_standard.md](../docs/reporting_standard.md)** —
tidy schema, split grains, fairness rules. All experiments report per this.

## Conventions
- **`common/`** holds reusable code (skill cards, audit gate, scoring, conditions,
  sandbox). Defined once; imported by every experiment. Never copy-paste it into a folder.
- Each **`E*/`** folder is a complete record: `config.json` (knobs) + `run.py` (thin
  orchestration) + `results/` (raw CSVs + `metrics.json`) + `README.md`
  (question/setup/reproduce) + **`RESULTS.md`** (display tables — placeholders until run).
- Folder names match plan IDs so this index ↔ `experiment_plan.md` stay in sync.
- **Scope-agnostic after E0:** E0 was the PM-only leakage diagnostic (done). From E1 on,
  every experiment runs **all domains** and **reports per scope** (per domain; PM also
  covered/uncovered as a leakage guardrail). `base` is each experiment's **in-run control**;
  `improved` is an optional PM-only leaky baseline.
- **Always report the per-scope held-out split**, never aggregate alone.
- Each `E*/README.md` has a **Reproduce** section with the exact command(s).

## Prerequisites (once)
```bash
conda activate ./.conda        # Python 3.10 env at repo root
# openai_key.txt at repo root (and openrouter_key.txt for llama/qwen — E6)
```
Always run **from the repo root**, e.g. `python experiments/E0_baselines/run.py`.

## ⚠️ Tool baseline changed at E1.7
E0–E1.5.5 used **original** tools. **From E1.7 onward the baseline is `improved` tools**
(`--use_improved_tools`, NO integration tests — team-comparable), temp 0 + API seed 42.
So E1.7+ numbers are **not directly comparable** to E1/E1.5.5 (different tools). `tool_set` is
now a config knob and is included in the store signature (no stale cross-tool reuse).

## Index

| ID | Folder | Question | Status |
|---|---|---|---|
| E0 | [E0_baselines](./E0_baselines/) | does the current method leak? (diagnostic) | ✅ done — leakage confirmed, not re-run |
| E0.5 | [E0_5_harness_sanity](./E0_5_harness_sanity/) | are non-PM domains really 0% or harness-broken? | ⬜ |
| E1 | [E1_skills_all](./E1_skills_all/) | do leakage-safe skills lift held-out accuracy? | ✅ done (+2.5, mixed) |
| E1.5 | [E1_5_skills_triggered](./E1_5_skills_triggered/) | trigger-gating via EMBEDDING (fragile; kept, not run) | ⬜ parked |
| E1.6 | [E1_6_gated_paramcomplete](./E1_6_gated_paramcomplete/) | does adding a parameter-completeness skill recover PM (held-out check)? | ⬜ next |
| E1.5.5 | [E1_5_5_skills_llm_gated](./E1_5_5_skills_llm_gated/) | trigger-gating via LLM classifier (better) | ✅ done (best: 48.7; PM artifact found) |
| E1.6 | [E1_6_gated_paramcomplete](./E1_6_gated_paramcomplete/) | +parameter-completeness skill (setup/scratch record) | ⬜ kept as record |
| E1.7 | [E1_7_improved_gated_skills](./E1_7_improved_gated_skills/) | **DEFINITIVE** base vs gated skills on IMPROVED tools (new baseline) | ✅ done — +7.5 overall / +11.2 real-task |
| E1.8 | [E1_8_verify_correct](./E1_8_verify_correct/) | actor-critic verify-and-correct MECHANISM (generic self-correction) | ⬜ ★ next (needs build) |
| E2 | [E2_skills_grounded](./E2_skills_grounded/) | do held-out micro-examples help small models follow skills? | ⬜ |
| E3 | [E3_example_bank](./E3_example_bank/) | do leakage-safe examples beat skills / leaky method? | ⬜ |
| E4 | [E4_retrieval](./E4_retrieval/) | does top-k retrieval beat inject-all / random; scale? | ⬜ |
| E5 | [E5_all_domains](./E5_all_domains/) | does the best method generalize across all 5 domains? | ⬜ |
| E7 | [E7_cross_dataset](./E7_cross_dataset/) | do WorkBench skills transfer to API-Bank? | ⬜ ★ headline |
| E8 | [E8_skill_derivation](./E8_skill_derivation/) | do failure-derived (bottom-up) skills beat hand-written? | ⬜ strengthening |

(E6 multi-model is optional/deferred — no folder until run.)

## Critical path
E0 ✅ → E0.5 → E1 → (E2 if needed) → E5 → E7.  (E0 done; live path starts at E0.5.)
