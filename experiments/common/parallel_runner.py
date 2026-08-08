"""Parallel launcher — size-balanced shards, with a config-keyed done-store for resume.

Splits the REMAINING (not-yet-done) work into `max_workers` equal shards and runs each in
its own process (WorkBench tools use module-global state → separate processes = safe).
Because completion is tracked in a config-keyed store (experiments.common.store), you can
stop and relaunch with a DIFFERENT shard count — only undone queries re-run. After the run,
new predictions are patched into the store, and the full store is scored/merged.

Usage: set "parallel": true (+ optional "max_workers", "stagger_seconds") in the config.
"""
import json
import os
import shutil
import subprocess
import sys
import time

import pandas as pd

from experiments.common.bootstrap import PROJECT_ROOT
from experiments.common.scoring import score, to_records, standard_table
from experiments.common.pricing import cost_usd
from experiments.common import store

_ENTRY = os.path.join(PROJECT_ROOT, "experiments", "common", "_run_one.py")


def _combined_gt(here, config):
    """Combine all domain query CSVs, tagging source_domain; also cache to raw/ for reference."""
    frames = []
    for qp in config["queries_paths"]:
        stem = os.path.basename(qp).replace("_queries_and_answers.csv", "")
        d = pd.read_csv(os.path.join(PROJECT_ROOT, qp))
        d["source_domain"] = stem
        frames.append(d)
    gt = pd.concat(frames, ignore_index=True)
    raw = os.path.join(here, "results", "raw")
    os.makedirs(raw, exist_ok=True)
    gt.to_csv(os.path.join(raw, "_combined_queries.csv"), index=False)
    return gt


def _make_work_shards(here, config, gt, remaining):
    """Round-robin the REMAINING (per-condition) queries into K shards; per-condition files."""
    par_dir = os.path.join(here, "results", "parallel")
    os.makedirs(par_dir, exist_ok=True)
    k = config.get("max_workers", 3)
    conds = config["conditions"]

    # assign each remaining (condition, query) to a shard, round-robin per condition
    shard_items = {s: {c: [] for c in conds} for s in range(k)}
    for c in conds:
        for i, q in enumerate(remaining[c]):
            shard_items[i % k][c].append(q)

    by_query = gt.set_index("query")
    units = []
    for s in range(k):
        cond_paths, any_work = {}, False
        ddir = os.path.join(par_dir, f"shard_{s:02d}")
        os.makedirs(os.path.join(ddir, "results", "raw"), exist_ok=True)
        for c in conds:
            qs = shard_items[s][c]
            if not qs:
                continue
            sub = by_query.loc[by_query.index.intersection(qs)].reset_index()
            qfile = os.path.join(ddir, f"_q_{c}.csv")
            sub.to_csv(qfile, index=False)
            cond_paths[c] = qfile
            any_work = True
        if not any_work:
            continue
        dcfg = {kk: v for kk, v in config.items() if kk not in ("queries_paths", "parallel", "max_workers")}
        dcfg["conditions"] = list(cond_paths.keys())
        dcfg["condition_queries"] = cond_paths
        with open(os.path.join(ddir, "config.json"), "w") as f:
            json.dump(dcfg, f, indent=2)
        units.append((f"shard_{s:02d}", ddir))
    return units


def _harvest_new(here, exp, condition):
    """Collect this run's fresh prediction rows from shard checkpoints for a condition."""
    import glob
    pat = os.path.join(here, "results", "parallel", "*", "results", "checkpoints",
                       f"{exp}_{condition}_chunk*.pkl")
    frames = [pd.read_pickle(p) for p in glob.glob(pat)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def run_parallel(here, config):
    conds = config["conditions"]
    exp = config["experiment"]
    gt = _combined_gt(here, config)
    all_q = gt["query"].tolist()

    # Capture any completed chunks from a prior (possibly INTERRUPTED) run into the store
    # BEFORE we compute remaining or wipe the shard dirs — so an interruption only loses the
    # in-progress chunk (≤ checkpoint_every queries), not the whole run.
    for c in conds:
        store.patch_done(here, config, c, _harvest_new(here, exp, c))

    # what's already done (config-keyed store) → remaining per condition
    remaining = {c: [q for q in all_q if q not in store.done_queries(here, config, c)] for c in conds}
    n_remaining = sum(len(v) for v in remaining.values())
    done_counts = {c: len(all_q) - len(remaining[c]) for c in conds}
    print(f"[parallel] store: done {done_counts}  |  remaining {sum(len(v) for v in remaining.values())} "
          f"query-runs across {conds}")

    if n_remaining > 0:
        max_workers = config.get("max_workers", 3)
        stagger = config.get("stagger_seconds", 8)
        shutil.rmtree(os.path.join(here, "results", "parallel"), ignore_errors=True)
        units = _make_work_shards(here, config, gt, remaining)
        print(f"[parallel] launching {len(units)} shards (max_workers={max_workers}, stagger={stagger}s)")

        t0 = time.time()
        running, done = [], []
        queue = list(units)
        while queue or running:
            while queue and len(running) < max_workers:
                stem, ddir = queue.pop(0)
                log = open(os.path.join(ddir, "run.log"), "w")
                p = subprocess.Popen([sys.executable, "-u", _ENTRY, ddir],
                                     stdout=log, stderr=subprocess.STDOUT, cwd=PROJECT_ROOT)
                running.append((stem, ddir, p, log))
                print(f"[parallel] started {stem} (pid {p.pid})")
                if queue and len(running) < max_workers:
                    time.sleep(stagger)
            for item in running[:]:
                stem, ddir, p, log = item
                if p.poll() is not None:
                    log.close()
                    running.remove(item)
                    done.append((stem, ddir))
                    print(f"[parallel] finished {stem}  ({len(done)}/{len(units)})  rc={p.returncode}")
            time.sleep(2)
        wall = time.time() - t0
        print(f"[parallel] shards done in {wall:.0f}s wall")

        # patch new predictions into the store
        for c in conds:
            store.patch_done(here, config, c, _harvest_new(here, exp, c))
    else:
        wall, units = 0.0, []
        print("[parallel] nothing remaining — merging from store")

    return _merge(here, config, gt, units, wall)


def _coerce_bool(df, col):
    if col in df.columns:
        df[col] = df[col].astype(str).str.lower().isin(["true", "1"])
    return df


def _merge(here, config, gt, units, wall):
    exp, model = config["experiment"], config["model"]
    scored, usage = {}, {}
    for c in config["conditions"]:
        full = store.load_done(here, config, c)      # authoritative: all completed preds
        scored[c] = score(full, gt) if len(full) else pd.DataFrame()

    # token/cost usage: this run's shards only (resumed work not recounted)
    for c in config["conditions"]:
        pt = ct = tot = 0; ov_pt = ov_ct = 0; ov_cost = 0.0; ov_by_tag = {}
        for stem, ddir in units:
            m = os.path.join(ddir, "results", "metrics.json")
            if not os.path.exists(m):
                continue
            u = json.load(open(m)).get("usage", {}).get(c)
            if u:
                pt += u.get("prompt_tokens", 0); ct += u.get("completion_tokens", 0); tot += u.get("total_tokens", 0)
                ov_pt += u.get("overhead_prompt_tokens", 0); ov_ct += u.get("overhead_completion_tokens", 0)
                ov_cost += u.get("overhead_cost_usd", 0) or 0
                for tag, v in (u.get("overhead_by_tag") or {}).items():
                    e = ov_by_tag.setdefault(tag, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
                    e["prompt_tokens"] += v.get("prompt_tokens", 0)
                    e["completion_tokens"] += v.get("completion_tokens", 0); e["calls"] += v.get("calls", 0)
        n = int(len(scored[c])) if len(scored[c]) else 0
        actor_cost = cost_usd(model, pt, ct)
        usage[c] = {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tot,
                    "cost_usd": actor_cost, "overhead_prompt_tokens": ov_pt,
                    "overhead_completion_tokens": ov_ct, "overhead_cost_usd": round(ov_cost, 6),
                    "overhead_by_tag": ov_by_tag,
                    "total_cost_incl_overhead": round((actor_cost or 0) + ov_cost, 6),
                    "wall_seconds": round(wall, 1), "n_scored": n,
                    "note": "tokens/cost are THIS run's new work only; cost_usd actor-only, "
                            "total_cost_incl_overhead adds gate+critic"}

    records = to_records({c: d for c, d in scored.items() if len(d)}, experiment=exp, model=model,
                         seed=config.get("seed", 1), coverage_split=config.get("coverage_split", False))
    print(f"\n########## {exp} — standard results (from store) ##########")
    print(standard_table(records))
    print(f"\n########## {exp} — cost / tokens (this run) ##########")
    for c, u in usage.items():
        cc = "-" if u["cost_usd"] is None else f"${u['cost_usd']:.4f}"
        print(f"  {c:<10} {u['total_tokens']:>10,} tokens  {cc}  (scored {u['n_scored']})")
    print(f"  wall (this run): {wall:.0f}s")

    raw = os.path.join(here, "results", "raw")
    os.makedirs(raw, exist_ok=True)
    for c, d in scored.items():
        if len(d):
            d.to_csv(os.path.join(raw, f"{exp}_{c}.csv"), index=False)
    with open(os.path.join(here, "results", "metrics.json"), "w") as f:
        json.dump({"config": config, "records": records, "usage": usage}, f, indent=2)
    print(f"\nWrote {os.path.join(here, 'results', 'metrics.json')}")
    return records
