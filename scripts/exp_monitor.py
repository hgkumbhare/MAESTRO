"""Pipeline health monitor for a parallel run — progress, step timing, and RATE-LIMIT stalls.

Parses each shard's run.log to surface where time goes and whether we're being throttled.

Usage:
    python scripts/exp_monitor.py                      # defaults to E1_skills_all
    python scripts/exp_monitor.py experiments/E5_all_domains
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)
from experiments.common import store  # noqa: E402

STALL_S = 30          # a step longer than this ≈ rate-limit backoff, not real latency
RECENT_N = 40         # look at the last N steps to judge "currently throttled?"

DUR_RE = re.compile(r"Duration ([0-9.]+) seconds")
# Explicit rate-limit error phrases only (bare "429" would match token counts like "138,429").
RL_RE = re.compile(r"RateLimitError|Too Many Requests|rate_limit_exceeded", re.IGNORECASE)


def parse_shard(log):
    if not os.path.exists(log):
        return None
    text = open(log, errors="ignore").read()
    queries = text.count("### Query:")
    durs = [float(x) for x in DUR_RE.findall(text)]
    rl_hits = len(RL_RE.findall(text))
    total = sum(durs)
    stalls = [d for d in durs if d > STALL_S]
    stall_t = sum(stalls)
    recent = durs[-RECENT_N:]
    recent_stalls = sum(1 for d in recent if d > STALL_S)
    return {
        "queries": queries, "steps": len(durs), "total_s": total,
        "stall_steps": len(stalls), "stall_s": stall_t,
        "rl_hits": rl_hits, "recent_stalls": recent_stalls, "recent_n": len(recent),
        "avg_step": (total / len(durs)) if durs else 0,
    }


def main():
    exp_dir = sys.argv[1] if len(sys.argv) > 1 else "experiments/E1_skills_all"
    exp_dir = os.path.join(REPO, exp_dir) if not os.path.isabs(exp_dir) else exp_dir
    cfg = json.load(open(os.path.join(exp_dir, "config.json")))
    conds = cfg["conditions"]

    # total queries expected (× conditions)
    if cfg.get("queries_paths"):
        total_q = sum(sum(1 for _ in open(os.path.join(REPO, p))) - 1 for p in cfg["queries_paths"])
    else:
        total_q = sum(1 for _ in open(os.path.join(REPO, cfg["queries_path"]))) - 1
    total_units = total_q * len(conds)

    running = subprocess.run(["pgrep", "-f", "_run_one.py"], capture_output=True).stdout.strip() != b""
    shards = sorted(glob.glob(os.path.join(exp_dir, "results", "parallel", "*", "run.log")))

    print(f"{cfg['experiment']}  ({'RUNNING' if running else 'idle'})  workers={cfg.get('max_workers')}  "
          f"engine={cfg.get('agent_engine')}")
    print(f"{'shard':<12}{'q done':>8}{'steps':>7}{'avg s':>7}{'stalls':>8}{'stall%':>8}{'429s':>6}{'recent':>8}")
    print("-" * 72)

    agg = {"q": 0, "steps": 0, "total": 0, "stall_s": 0, "stall_steps": 0, "rl": 0, "recent": 0}
    for log in shards:
        s = parse_shard(log)
        if not s:
            continue
        name = os.path.basename(os.path.dirname(log))
        stallpct = 100 * s["stall_s"] / s["total_s"] if s["total_s"] else 0
        flag = "  <== throttled" if s["recent_stalls"] else ""
        recent_str = f"{s['recent_stalls']}/{s['recent_n']}"
        print(f"{name:<12}{s['queries']:>8}{s['steps']:>7}{s['avg_step']:>7.1f}"
              f"{s['stall_steps']:>8}{stallpct:>7.0f}%{s['rl_hits']:>6}"
              f"{recent_str:>8}{flag}")
        agg["q"] += s["queries"]; agg["steps"] += s["steps"]; agg["total"] += s["total_s"]
        agg["stall_s"] += s["stall_s"]; agg["stall_steps"] += s["stall_steps"]
        agg["rl"] += s["rl_hits"]; agg["recent"] += s["recent_stalls"]

    print("-" * 72)
    stallpct = 100 * agg["stall_s"] / agg["total"] if agg["total"] else 0
    print(f"{'TOTAL':<12}{agg['q']:>8}{agg['steps']:>7}{'':>7}{agg['stall_steps']:>8}{stallpct:>7.0f}%{agg['rl']:>6}")
    print()
    # live  = queries seen in shard logs this run (in-flight, may not be checkpointed yet)
    # saved = store (prior runs) + checkpointed chunks this run (what survives a crash)
    store_done = sum(len(store.done_queries(exp_dir, cfg, c)) for c in conds)
    chunk = cfg.get("checkpoint_every", 25)
    ckpt_pkls = glob.glob(os.path.join(exp_dir, "results", "parallel", "*",
                                       "results", "checkpoints", "*.pkl"))
    saved = store_done + len(ckpt_pkls) * chunk  # ~chunk per pkl (last chunks may be smaller)
    # per-condition breakdown — total spans all conditions; some may be seeded/reused
    n_q = total_units // max(len(conds), 1)
    per_cond = {c: len(store.done_queries(exp_dir, cfg, c)) for c in conds}
    print(f"conditions ({len(conds)} x {n_q} = {total_units} query-runs; total spans all conditions):")
    for c in conds:
        tag = "seeded/done" if per_cond[c] >= n_q else ("running" if running else "pending")
        print(f"    {c:<24}{per_cond[c]:>5}/{n_q}   {tag}")
    print(f"progress (live, in-flight):   {agg['q']:>5}/{total_units} ({100*agg['q']/total_units:.0f}%)")
    print(f"progress (saved/recoverable): {saved:>5}/{total_units} ({100*saved/total_units:.0f}%)"
          f"   [store {store_done} + {len(ckpt_pkls)} chunks x {chunk}]")
    print(f"time in rate-limit stalls: {stallpct:.0f}%   "
          f"({'⚠️  THROTTLED — reduce workers' if stallpct > 25 else 'ok'})")
    if agg["recent"] > 0:
        print(f"currently throttled: {agg['recent']} recent stalls across shards ⚠️")


if __name__ == "__main__":
    main()
