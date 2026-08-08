# Functionality guide — the experiment system

Everything you need to **run an experiment, read its results, and understand the machinery** built on
top of the WorkBench repo. If you're new, read this top-to-bottom once, then keep it as reference.

Companion docs in this folder:
- [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) — the *what* and *why*: every experiment E0→E1.11, run vs not.
- [prompt_structure.md](prompt_structure.md) — the *prompt*: what the agent actually sees, and where skills are injected.

---

## 1. Repo map — where things live

```
openai_key.txt            inference API key (OpenAI)                    ← you add this
openai_admin_key.txt      admin key for spend/usage scripts (optional)  ← you add this
openrouter_key.txt        OpenRouter key for llama/qwen (optional)      ← you add this

src/evals/constants.py    ALL result-affecting knobs (temp, seed, retries)   ← tune here
src/evals/utils.py        generate_results(): the one inference path both engines share
src/tools/                original WorkBench tools
src/tools_improved/       improved tool descriptions (team standard)
src/tools_smolagents/     smolagents-wrapped tools + GLOBAL_TOOL_TRACKER

experiments/common/       the shared machinery (see §7–§9)
  conditions.py             the treatments (base / skills / skills_gated / ..._verify)
  runner.py                 config-driven single-process runner + checkpointing
  parallel_runner.py        size-balanced sharded runner
  store.py                  the resumable done-store (backup mechanism)
  skills.py                 the skill cards
  triggers.py               the LLM/embedding skill gate
  critic.py                 the actor-critic critic (verify-and-correct)
  scoring.py                scoring + tidy record schema + standard table

experiments/E*/           one folder per experiment (see §4)
scripts/                  monitoring + cost tooling (see §10–§11)
docs/start_here/          THIS folder — read first
```

---

## 2. API keys & secrets — where to add them

All keys are **plain-text files in the repo root**, one token per file (read with `open(...).read()`).

| file | purpose | used by |
|---|---|---|
| `openai_key.txt` | inference (gpt-4o, gpt-4o-mini) + the LLM gate + the critic | `src/evals/utils.py`, `triggers.py`, `critic.py` |
| `openrouter_key.txt` | routes `llama3.3-70b`, `llama3.1-8b`, `qwen-2.5-72b`, `qwen-2.5-7b` | `src/evals/utils.py` |
| `openai_admin_key.txt` | **Admin** key for the spend/usage scripts (NOT inference) | `scripts/check_*` |

These files are git-ignored. To add cross-provider models, just drop `openrouter_key.txt` in the root —
no code change needed; the model ids are already wired in `AVAILABLE_LLMS`.

---

## 3. Constants — the knobs that affect results

**Single source of truth: [`src/evals/constants.py`](../../src/evals/constants.py).** Both engines
import from here, so langchain and smolagents can't drift (they used to: temp 0 vs 0.7 — a real bug).

| constant | value | what it does |
|---|---|---|
| `TEMPERATURE` | `0` | greedy decoding — max accuracy + reproducible (WorkBench has one correct outcome/task) |
| `SEED` | `42` | best-effort reproducibility for agent + gate (OpenAI seed is best-effort, not a guarantee) |
| `RETRY_TEMPERATURE` | `0.5` | only the langchain "no actions taken" retry path |
| `MAX_ITERATIONS` | `20` | langchain ReAct step cap |
| `MAX_EXECUTION_TIME` | `120` | langchain per-query seconds cap |
| `SMOLAGENTS_RETRY_WAIT` | `10` | rate-limit backoff base (smolagents default 60 → up to ~3min stalls; 10 is enough on Tier 2) |
| `SMOLAGENTS_RETRY_MAX_ATTEMPTS` | `3` | retry attempts on 429s |

Change a knob here → it applies everywhere. **`TEMPERATURE` and `SEED` are shared by baseline AND every
treatment**, so all conditions are decoded identically — the only thing that varies is the treatment.

---

## 4. Anatomy of an experiment folder

```
experiments/E1_7_improved_gated_skills/
  config.json      the experiment definition (§5)
  run.py           thin wrapper: load config → run_experiment / run_parallel
  README.md        what this experiment is + how to run it
  commands.md      copy-paste commands
  RESULTS.md       the written-up findings (hand-authored from metrics.json)
  results/
    metrics.json   THE machine output: {config, records (tidy), usage}
    raw/*.csv      per-query predictions + correctness, one CSV per condition
    done_store/    the resumable backup (§8) — *.pkl keyed by config signature
    parallel/      per-shard working dirs + run.log (parallel runs only)
    checkpoints/   chunk checkpoints (single-process runs)
```

Every experiment is the **same code path** (`generate_results`) with only the config differing — so
results are comparable across experiments by construction.

---

## 5. `config.json` — every key

```jsonc
{
  "experiment": "E1_7",                 // id; part of the store signature
  "model": "gpt-4o-mini-2024-07-18",    // single-model runs
  "models": ["...", "..."],             // multi-model runs (E1.9) — loop, one at a time
  "queries_path":  "data/.../x.csv",    // single domain, OR
  "queries_paths": ["...", "..."],      // multiple domains concatenated into one run
  "conditions": ["base", "skills_gated"],   // which treatments to run (§6)
  "agent_engine": "smolagents",         // "smolagents" or "langchain"
  "tool_set": "improved",               // "original" or "improved" — RUN-LEVEL (all conditions share it)
  "gating": { "method": "llm" },        // "llm" (classifier) or "embedding" (cosine+threshold)
  "verify": { "max_iters": 2, "critic_model": "gpt-4o-mini-2024-07-18" },  // actor-critic (§7c)
  "checkpoint_every": 25,               // backup every N queries (0 disables) (§8)
  "parallel": true,                     // use the sharded runner (§9)
  "max_workers": 6,                     // number of concurrent shards (§9)
  "stagger_seconds": 8,                 // delay between shard launches (avoids a thundering herd)
  "seed": 1,                            // reporting seed label (decoding seed is constants.SEED)
  "coverage_split": false               // report covered/uncovered split (E0 leakage analysis)
}
```

---

## 6. Conditions — what's shared vs what varies

Conditions live in [`experiments/common/conditions.py`](../../experiments/common/conditions.py). **Every
condition runs the identical inference path** — same model, tools, temperature, seed, iteration caps.
Only the *treatment* differs:

| condition | integration tests | skills | verify | notes |
|---|---|---|---|---|
| `base` | ✗ | none | ✗ | the control |
| `improved` | ✓ (LEAKY) | none | ✗ | the original paper method (E0 only) |
| `skills` | ✗ | all (always-on) | ✗ | E1 |
| `skills_gated` | ✗ | gated per query | ✗ | E1.5.5 / E1.7 |
| `skills_gated_verify` | ✗ | gated per query | ✓ | E1.8 |

**Shared by baseline AND treatment** (so comparisons are fair): `model`, `tool_set`, `agent_engine`,
`TEMPERATURE`, `SEED`, `MAX_ITERATIONS`, `MAX_EXECUTION_TIME`, and the query set. **`tool_set` is
run-level**, not per-condition — base and treatment always use the *same* tools; only the skills /
verify wrapper changes. That's the whole point: any accuracy delta is attributable to the treatment,
nothing else.

---

## 7. The mechanisms

### (a) Skills — [`skills.py`](../../experiments/common/skills.py)
8 dataset-agnostic cards (identifier-resolution, fetch-before-act, reuse-returned-value,
no-duplicate-calls, read-output, parameter-completeness, right-tool-selection, tool-required). They
teach *tool-interaction competence*, never eval answers → leakage-safe. Injected as extra system prompt.

### (b) Gating — [`triggers.py`](../../experiments/common/triggers.py)
Instead of injecting all 8 cards always, inject only the ones a query needs.
- `method: "llm"` — one classifier call per query asks which skills apply. **No threshold to tune**
  (so no eval-tuning leakage). Default; used by E1.7/E1.8.
- `method: "embedding"` — cosine similarity of query vs card triggers > `threshold`. Cheaper, blunter.

### (c) Actor-critic verify-and-correct — [`critic.py`](../../experiments/common/critic.py)
A general self-correction loop (not per-failure patches):
1. Actor runs the task, produces a tool trace.
2. **Critic reads task + trace *with tool outputs* — NEVER the gold answer** (that would be test-set
   access) — and replies `PASS` or `FAIL: <one specific fix>`.
3. On `FAIL`, the actor redoes the task with that feedback, up to `verify.max_iters` (default 2).

Enabled by the `skills_gated_verify` condition + `verify` config block. The critic is deliberately
gold-blind so the mechanism is honest and would work outside the benchmark.

### (d) Tool dependency graph — [`E1_11_.../graph.py`](../../experiments/E1_11_tool_dependency_graph/graph.py)
Explicit producer→consumer graph (e.g. `search_emails --email_id--> delete_email`) derived from tool
signatures (leakage-safe). Injected as structure. Scaffold — see its README.

---

## 8. Backup mechanism — the resumable done-store

[`experiments/common/store.py`](../../experiments/common/store.py). This is what makes runs
**crash-proof and resumable**, and lets you change shard count mid-experiment.

- Every completed query's prediction is saved to `results/done_store/<signature>.pkl`.
- The **signature** = `experiment · condition · model · agent_engine · tool_set · temperature`.
  Because it's keyed by *config* (not by shard), you can stop a 6-shard run and resume with 3 shards —
  only unfinished queries re-run.
- **Two backup layers:**
  1. `done_store/` — the authoritative, config-keyed record (survives everything).
  2. `checkpoint_every: N` — during a run, every N queries are pickled to `checkpoints/` (or harvested
     into the store between shard batches). An interruption loses at most the in-flight chunk (≤ N).
- **Resume:** just re-run `run.py`. It reads the store, skips done queries, runs the rest, merges back.
- **Seed one experiment from another:** `store.seed_from(...)` copies completed predictions across
  experiments with identical config (e.g. E1.8 reuses E1.7's `base` + `skills_gated` for free).
- **Start fresh:** delete `results/done_store/` (and `results/checkpoints/`).

---

## 9. Sharding & parallelism — how to increase shards

[`experiments/common/parallel_runner.py`](../../experiments/common/parallel_runner.py). Set
`parallel: true` and it splits the remaining queries into **size-balanced shards** (separate processes,
for global-state safety), each writing to `results/parallel/<shard>/`.

**To increase/decrease shards, edit two config keys:**
- `max_workers` — how many shards run concurrently. **This is your throughput dial.**
- `stagger_seconds` — delay between launches so they don't all hit the API at once.

**Rate-limit reality:** more shards ≠ always faster. On OpenAI **Tier 1** (200k TPM), 6 shards spend
~74% of time in backoff stalls; on **Tier 2** (2M TPM) they run clean. Watch `exp_monitor.py`'s
`time in rate-limit stalls` — if it's >25%, reduce `max_workers`. The store makes this safe: kill the
run, lower `max_workers`, re-run — it resumes from the store with no lost work.

---

## 10. Running an experiment

```bash
# any experiment: one command, resumable
python experiments/E1_7_improved_gated_skills/run.py

# multi-model (E1.9): all models sequentially, or one
python experiments/E1_9_multi_model/run.py
python experiments/E1_9_multi_model/run.py gpt-4o-2024-08-06
```

Each experiment's `commands.md` has its exact invocations. `run.py` is always safe to re-run (§8).

---

## 11. Reading results — the scripts + the files

**Live monitoring (while it runs):**
| script | shows |
|---|---|
| `python scripts/exp_monitor.py experiments/E1_8_verify_correct` | health: per-shard throughput, step timing, **rate-limit stalls**, per-condition breakdown |
| `python scripts/exp_status.py experiments/E1_8_verify_correct` | cumulative progress from the store (shard-count independent) |
| `python scripts/exp_progress.py experiments/E1_8_verify_correct` | quick per-shard query counts |

**Final numbers:**
- `results/metrics.json` — the machine truth: `{config, records, usage}`. `records` is a **tidy** list
  of `{condition, domain, split, n, accuracy, side_effect_rate, delta_vs_base}` rows. The runner also
  prints a `standard_table` at the end of a run.
- `results/raw/*.csv` — per-query predictions + correctness (for error analysis).
- `RESULTS.md` — the hand-written findings for that experiment.
- Multi-model cross table: `python experiments/E1_9_multi_model/crunch.py`.

**Overall accuracy** is the n-weighted mean of the per-domain `accuracy` rows (records are per
condition×domain). Always also report the **non-empty-gold split** — aggregate accuracy under-credits
a capable agent because some WorkBench tasks reward inaction (see EXPERIMENT_LOG §Caveats).

**Cost / efficiency.** `experiments/common/pricing.py` maps tokens→USD (`cost_usd`) and computes
`cost_report` → total $, **$/query**, and **$/correct** (cost to solve one task — the honest
efficiency metric; a method that costs more per query but solves more can be *cheaper per correct
answer*). The crunch scripts print a cost table; E1.9's is the small-vs-big "money chart". Caveat:
token capture is **actor-only** — the gate + critic calls bypass the litellm callback, so gated/verify
costs are a few % low until that overhead is metered.

**Cost & usage (needs `openai_admin_key.txt`):**
| script | shows |
|---|---|
| `python scripts/check_openai_spend.py` | $ spend (Admin Costs API) |
| `python scripts/check_usage.py` | tokens/requests per model (Admin Usage API) |
| `python scripts/check_rate_limit.py` | your current TPM/RPM (from response headers) |
| `python scripts/check_project_limits.py` | per-project/model limits (are you sharing a tier?) |

---

## 12. Quickstart for a new person

1. Put `openai_key.txt` in the repo root (add `openrouter_key.txt` if using llama/qwen).
2. Read [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) for the story, [prompt_structure.md](prompt_structure.md) for what the agent sees.
3. Run a cheap one: `python experiments/E1_7_improved_gated_skills/run.py` (it resumes from the store instantly if already done).
4. Watch it: `python scripts/exp_monitor.py experiments/E1_7_improved_gated_skills`.
5. Read it: open `results/metrics.json` / `RESULTS.md`.
6. To make a new experiment: copy an `E*/` folder, edit `config.json` (§5), run `run.py`.
