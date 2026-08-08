"""Config-driven experiment runner (scope-agnostic).

Every experiment's run.py is a thin wrapper around run_experiment(here, config). The
config picks model / queries / conditions; the runner scores each condition, writes
per-query CSVs + metrics.json (tidy schema), and prints the standard table.

config keys:
  experiment      : id string (e.g. "E1")
  model           : model name
  queries_path    : single CSV path (relative to repo root), OR
  queries_paths   : list of CSV paths — concatenated into one all-domains run
  conditions      : list of condition names (base / improved / skills)
  include_demo    : bool (skills grounding, E2) — optional
  seed            : int — optional
  checkpoint_every: int — save a resume checkpoint every N queries (default 25, 0 disables)

Resume: re-running run.py reuses completed chunk checkpoints in results/checkpoints/ and
only re-runs the unfinished ones. Delete results/checkpoints/ to start fresh.
"""
import glob
import json
import os
import time
import contextlib

import pandas as pd

from experiments.common.bootstrap import PROJECT_ROOT
from experiments.common.conditions import run_condition
from experiments.common.scoring import score, to_records, standard_table
from experiments.common.pricing import cost_usd
from experiments.common.litellm_usage import litellm_token_callback

# Token/cost tracking via LangChain's OpenAI callback (import location varies by version).
try:
    from langchain_community.callbacks import get_openai_callback
except Exception:  # pragma: no cover
    try:
        from langchain.callbacks import get_openai_callback
    except Exception:
        get_openai_callback = None


class _NullCB:
    prompt_tokens = completion_tokens = total_tokens = 0
    total_cost = None


def _token_ctx(agent_engine):
    """Pick the right token-capture context for the engine (smolagents=LiteLLM, else langchain)."""
    if agent_engine == "smolagents":
        return litellm_token_callback()
    if get_openai_callback is not None:
        return get_openai_callback()
    return contextlib.nullcontext(_NullCB())


def _resolve_queries(here: str, config: dict) -> str:
    """Return a single CSV path. If multiple domains are given, concat them into one."""
    raw = os.path.join(here, "results", "raw")
    if config.get("queries_paths"):
        frames = [pd.read_csv(os.path.join(PROJECT_ROOT, p)) for p in config["queries_paths"]]
        combined = pd.concat(frames, ignore_index=True)
        out = os.path.join(raw, "_combined_queries.csv")
        combined.to_csv(out, index=False)
        return out
    return os.path.join(PROJECT_ROOT, config["queries_path"])


def _run_condition_checkpointed(exp, cond, queries_path, model, ckpt_dir, chunk_size,
                                include_demo, agent_engine, gate_threshold=0.35,
                                gate_method="embedding", tool_set="original", verify_cfg=None):
    """Run one condition in chunks, checkpointing after each. Resumes from existing chunks.

    Returns (preds_df, usage_dict). Checkpoints are pickled (preserves list-valued columns).
    """
    all_q = pd.read_csv(queries_path)
    n = len(all_q)
    if not chunk_size or chunk_size <= 0:
        chunk_size = n  # single chunk = no checkpointing
    chunks = [all_q.iloc[i:i + chunk_size] for i in range(0, n, chunk_size)]

    from experiments.common import usage_meter

    parts, pt, ct, tot, lc_cost, wall = [], 0, 0, 0, 0.0, 0.0
    ov_pt = ov_ct = 0; ov_cost = 0.0; ov_by_tag = {}
    for k, ch in enumerate(chunks):
        ckpt = os.path.join(ckpt_dir, f"{exp}_{cond}_chunk{k:03d}.pkl")
        if os.path.exists(ckpt):
            parts.append(pd.read_pickle(ckpt))
            print(f"  [resume] {cond} chunk {k + 1}/{len(chunks)} loaded from checkpoint")
            continue
        chunk_q = os.path.join(ckpt_dir, f"_q_{exp}_{cond}_chunk{k:03d}.csv")
        ch.to_csv(chunk_q, index=False)
        t0 = time.time()
        meter_before = usage_meter.totals()  # gate/critic overhead for THIS chunk only
        with _token_ctx(agent_engine) as cb:
            preds = run_condition(cond, chunk_q, model, include_demo=include_demo,
                                  agent_engine=agent_engine, gate_threshold=gate_threshold,
                                  gate_method=gate_method, tool_set=tool_set, verify_cfg=verify_cfg)
        d = usage_meter.delta(meter_before, usage_meter.totals())
        ov_pt += d["overhead_prompt_tokens"]; ov_ct += d["overhead_completion_tokens"]
        ov_cost += d["overhead_cost_usd"]
        for tag, v in d["overhead_by_tag"].items():
            e = ov_by_tag.setdefault(tag, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
            e["prompt_tokens"] += v["prompt_tokens"]; e["completion_tokens"] += v["completion_tokens"]
            e["calls"] += v["calls"]
        pt += getattr(cb, "prompt_tokens", 0); ct += getattr(cb, "completion_tokens", 0)
        tot += getattr(cb, "total_tokens", 0); lc_cost += (getattr(cb, "total_cost", 0) or 0)
        wall += time.time() - t0
        preds.to_pickle(ckpt)
        parts.append(preds)
        print(f"  [ckpt] {cond} chunk {k + 1}/{len(chunks)} saved ({len(ch)} queries)")

    preds_all = pd.concat(parts, ignore_index=True)
    actor_cost = cost_usd(model, pt, ct)
    usage = {
        "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tot,
        "cost_usd": actor_cost,  # actor only (back-compat: existing readers expect actor cost here)
        "overhead_prompt_tokens": ov_pt, "overhead_completion_tokens": ov_ct,
        "overhead_cost_usd": round(ov_cost, 6), "overhead_by_tag": ov_by_tag,
        "total_cost_incl_overhead": round((actor_cost or 0) + ov_cost, 6),
        "langchain_cost_usd": round(lc_cost, 6) if lc_cost else lc_cost,
        "wall_seconds": round(wall, 1),
        "sec_per_query": round(wall / n, 2) if n else None,
        "n_queries": n,
        "note": "token/cost/latency cover freshly-run chunks only (resumed chunks not recounted); "
                "cost_usd is actor-only, total_cost_incl_overhead adds gate+critic.",
    }
    return preds_all, usage


def run_experiment(here: str, config: dict):
    raw = os.path.join(here, "results", "raw")
    ckpt_dir = os.path.join(here, "results", "checkpoints")
    os.makedirs(raw, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    chunk_size = config.get("checkpoint_every", 25)
    # Per-condition query files (set by the parallel runner for resumable resharding);
    # otherwise all conditions share one resolved queries file.
    condition_queries = config.get("condition_queries")
    default_qpath = None if condition_queries else _resolve_queries(here, config)

    scored = {}
    usage = {}
    for cond in config["conditions"]:
        qpath = (os.path.join(PROJECT_ROOT, condition_queries[cond])
                 if condition_queries else default_qpath)
        print(f"\n=== {config['experiment']}: condition '{cond}' (checkpoint every {chunk_size}) ===")
        preds, usage[cond] = _run_condition_checkpointed(
            config["experiment"], cond, qpath, config["model"],
            ckpt_dir, chunk_size, config.get("include_demo", False),
            config.get("agent_engine", "langchain"),
            config.get("gating", {}).get("threshold", 0.35),
            config.get("gating", {}).get("method", "embedding"),
            config.get("tool_set", "original"), config.get("verify"))
        df = score(preds, pd.read_csv(qpath))
        df.to_csv(os.path.join(raw, f"{config['experiment']}_{cond}.csv"), index=False)
        scored[cond] = df

    records = to_records(scored, experiment=config["experiment"], model=config["model"],
                         seed=config.get("seed", 1),
                         coverage_split=config.get("coverage_split", False))
    print(f"\n########## {config['experiment']} — standard results ##########")
    print(standard_table(records))
    print(f"\n########## {config['experiment']} — cost / tokens / latency ##########")
    print(_usage_table(usage))

    with open(os.path.join(here, "results", "metrics.json"), "w") as f:
        json.dump({"config": config, "records": records, "usage": usage}, f, indent=2)
    print(f"\nWrote {os.path.join(here, 'results', 'metrics.json')}")
    return records


def _usage_table(usage: dict) -> str:
    hdr = f"{'condition':<12}{'tokens':>12}{'cost $':>10}{'wall s':>9}{'s/query':>9}"
    lines = [hdr, "-" * len(hdr)]
    tt = tc = tw = 0
    for cond, u in usage.items():
        cost = "-" if u["cost_usd"] is None else f"{u['cost_usd']:.4f}"
        lines.append(f"{cond:<12}{u['total_tokens']:>12,}{cost:>10}{u['wall_seconds']:>9.0f}{u['sec_per_query']:>9}")
        tt += u["total_tokens"]; tc += (u["cost_usd"] or 0); tw += u["wall_seconds"]
    lines.append(f"{'TOTAL':<12}{tt:>12,}{tc:>10.4f}{tw:>9.0f}{'':>9}")
    return "\n".join(lines)
