# Findings so far — results, cost, and how to reproduce

The headline results of the project to date, the cost story, and the one command that regenerates any
of these tables. For the full experiment-by-experiment history see [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## Setup (all numbers below)
gpt-4o-mini · smolagents · **improved tools** (team standard, no leaky integration tests) · temp 0 +
seed 42 · all 6 WorkBench domains (690 tasks). Accuracy = outcome-based (execute predicted calls, diff
DB state vs gold). SE = side-effect rate (wrong answer *with* a harmful write).

## Headline: accuracy

| condition | overall acc | Δ base | non-empty acc | Δ base | side-effects |
|---|---|---|---|---|---|
| base | 50.6 | — | 44.4 | — | 38.1 |
| **skills_gated** | 58.1 | **+7.5** | 55.6 | **+11.2** | 35.2 |
| **skills_gated_verify** | **60.4** | **+9.8** | **57.7** | **+13.3** | **32.5** |

- **Gated skills** (E1.7): leakage-safe tool-interaction skills, injected per query by an LLM gate
  (no threshold to tune). +7.5 overall, +11.2 on real tasks.
- **Verify-and-correct** (E1.8b): an actor-critic loop where a gold-blind critic reviews the trace and
  triggers a redo. Best condition on **every** metric — accuracy, real-task accuracy, and lowest
  side-effects.

### The empty-gold caveat (always report the non-empty split)
122 of 690 tasks have gold = "do nothing". A base agent that fails to act scores *correct* there, so
**aggregate accuracy under-credits a capable agent**. The non-empty-gold column is the honest metric —
and it's where the method looks strongest (+13.3). This artifact also bit the critic itself: v1's
"found nothing → retry" heuristic broke empty-gold tasks (net −12); the fix (empty-is-often-correct)
flipped that to +4 while improving real tasks (+8 → +12), for net **−4 → +16** queries.

## Headline: cost / efficiency
The thesis: a **small model + this method** reaches strong accuracy at low cost. The honest metric is
**$ per correct answer** (cost to actually solve one task):

| condition | cost $ | $/query | **$/correct** |
|---|---|---|---|
| base | 5.27 | 0.0076 | 0.0151 |
| **skills_gated** | 5.70 | 0.0083 | **0.0142** ⬅ cheapest per solved task |
| skills_gated_verify | 8.39 | 0.0122 | 0.0201 |

- **Gated skills is cheaper per correct answer than the baseline** (+8% spend, but 52 more tasks
  solved) — accuracy that pays for itself.
- **Verify maximizes accuracy + minimizes harm at ~1.5× cost** (its 57% retry rate roughly doubles
  actor tokens on retried queries). Choose by objective: gated for efficiency, verify for max accuracy.
- Overhead (the gate + critic calls) is now **metered** and is <1% of actor cost (~$0.00006/gate
  call, ~$0.00007/critic call). The big-vs-small "money chart" is E1.9 (not yet run).

## Reproduce any of this — one command
```bash
# accuracy + non-empty split + side-effects + cost, for ANY experiment folder:
python scripts/crunch_results.py experiments/E1_8b_verify_correct_v2
python scripts/crunch_results.py experiments/E1_7_improved_gated_skills
```
It scores each condition from the done-store (authoritative, shard-count independent) and prints the
tables above, writing `results/crunch_summary.json`. Cost reads `results/metrics.json` (actor) +
metered gate/critic overhead. See [FUNCTIONALITY.md](FUNCTIONALITY.md) §11 for the other read tools
(`exp_monitor`, `exp_status`) and the cost internals (`experiments/common/pricing.py`,
`usage_meter.py`).

## Where the mechanisms live
| piece | file |
|---|---|
| skill cards | `experiments/common/skills.py` |
| LLM skill gate | `experiments/common/triggers.py` |
| actor-critic critic | `experiments/common/critic.py` |
| token→\$ pricing + `$/correct` | `experiments/common/pricing.py` |
| overhead metering (gate+critic) | `experiments/common/usage_meter.py` |
| resumable done-store | `experiments/common/store.py` |
