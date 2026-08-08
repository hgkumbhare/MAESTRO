"""Crunch any experiment's results — accuracy, non-empty-gold split, side-effects, and COST.

Scores each condition from the done-store against ground truth (authoritative, shard-count
independent) and prints:
  1. Overall accuracy + side-effect rate per condition (Δ vs base).
  2. Non-empty-gold split (the honest metric — WorkBench rewards inaction on empty-gold tasks).
  3. Cost / efficiency: $/query and $ per CORRECT answer, actor + gate/critic overhead when metered.

Usage:
    python scripts/crunch_results.py experiments/E1_8b_verify_correct_v2
    python scripts/crunch_results.py experiments/E1_7_improved_gated_skills --base base

Notes:
  * Cost reads results/metrics.json `usage` when present, else harvests results/parallel/*/…/metrics.json.
    `cost_usd` is actor-only; `total_cost_incl_overhead` adds the gate + critic calls (metered runs).
  * Scoring re-executes tool calls, so a full experiment takes a couple of minutes.
"""
import argparse
import ast
import glob
import json
import os
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)

from experiments.common import store
from experiments.common.scoring import score
from experiments.common.pricing import cost_report


def _empty(gt):
    v = ast.literal_eval(gt) if isinstance(gt, str) else gt
    return len(v) == 0


def _combined_gt(config):
    if config.get("queries_paths"):
        return pd.concat([pd.read_csv(os.path.join(REPO, qp)) for qp in config["queries_paths"]],
                         ignore_index=True)
    return pd.read_csv(os.path.join(REPO, config["queries_path"]))


def _overall(df):
    return {"n": int(len(df)),
            "accuracy": round(100.0 * df["correct"].mean(), 1) if len(df) else None,
            "side_effect_rate": round(100.0 * df["unwanted_side_effects"].mean(), 1) if len(df) else None}


def _usage(exp_dir, config, cond):
    """Per-condition token usage: prefer results/metrics.json, else harvest shard metrics.json."""
    mj = os.path.join(exp_dir, "results", "metrics.json")
    if os.path.exists(mj):
        u = json.load(open(mj)).get("usage", {}).get(cond)
        if u and (u.get("prompt_tokens") or u.get("completion_tokens")):
            return u
    pt = ct = ov = 0.0
    for m in glob.glob(os.path.join(exp_dir, "results", "parallel", "*", "results", "metrics.json")):
        u = json.load(open(m)).get("usage", {}).get(cond)
        if u:
            pt += u.get("prompt_tokens", 0); ct += u.get("completion_tokens", 0)
            ov += u.get("overhead_cost_usd", 0) or 0
    return {"prompt_tokens": pt, "completion_tokens": ct, "overhead_cost_usd": ov} if (pt or ct) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp_dir", help="path to an experiment folder (has config.json)")
    ap.add_argument("--base", default="base", help="condition to use as the Δ baseline")
    args = ap.parse_args()

    exp_dir = args.exp_dir if os.path.isabs(args.exp_dir) else os.path.join(REPO, args.exp_dir)
    config = json.load(open(os.path.join(exp_dir, "config.json")))
    conds = config["conditions"]
    gt = _combined_gt(config)
    empty_q = set(gt.loc[gt["answer"].apply(_empty), "query"]) if "answer" in gt.columns else set()

    print(f"Scoring {len(conds)} conditions from the store (executes tool calls; ~1-2 min)...")
    scored = {}
    for c in conds:
        preds = store.load_done(exp_dir, config, c)
        scored[c] = score(preds, gt) if len(preds) else pd.DataFrame()

    print("\n" + "=" * 82)
    print(f"{config['experiment']}  —  {config.get('model')}  ·  tools={config.get('tool_set','original')}"
          f"  ·  engine={config.get('agent_engine','langchain')}")
    print("=" * 82)

    base = args.base if args.base in scored else conds[0]

    def acc_table(title, mask=None):
        print(f"\n## {title}")
        hdr = f"{'condition':<24}{'n':>5}{'acc %':>9}{'Δbase':>8}{'SE %':>8}{'ΔbaseSE':>9}"
        print(hdr); print("-" * len(hdr))
        bsub = scored[base] if mask is None else scored[base][scored[base]["query"].apply(mask)]
        bo = _overall(bsub)
        for c in conds:
            d = scored[c] if mask is None else scored[c][scored[c]["query"].apply(mask)]
            o = _overall(d)
            if o["accuracy"] is None:
                print(f"{c:<24}{o['n']:>5}   (no predictions)"); continue
            da = "" if c == base else f"{o['accuracy']-bo['accuracy']:>+8.1f}"
            ds = "" if c == base else f"{o['side_effect_rate']-bo['side_effect_rate']:>+9.1f}"
            print(f"{c:<24}{o['n']:>5}{o['accuracy']:>9.1f}{da:>8}{o['side_effect_rate']:>8.1f}{ds:>9}")

    acc_table("Overall (all queries)")
    if empty_q:
        acc_table(f"Non-empty-gold only ({len(empty_q)} empty-gold excluded)",
                  mask=lambda q: q not in empty_q)

    # ---- cost ----
    print("\n## Cost / efficiency")
    hdr = f"{'condition':<24}{'tokens':>13}{'actor $':>9}{'+ovhd $':>9}{'$/query':>10}{'$/correct':>11}"
    print(hdr); print("-" * len(hdr))
    model = config["model"]
    cost_out = {}
    for c in conds:
        u = _usage(exp_dir, config, c)
        o = _overall(scored[c])
        if not u or o["accuracy"] is None:
            print(f"{c:<24}   (no usage in this run — seeded/reused? see the source experiment)")
            continue
        pt = int(u.get("prompt_tokens", 0)); ct = int(u.get("completion_tokens", 0))
        ncorr = o["accuracy"] / 100.0 * o["n"]
        r = cost_report(model, pt, ct, o["n"], ncorr)
        total_incl = u.get("total_cost_incl_overhead")
        if total_incl is None:
            total_incl = (r["cost_usd"] or 0) + (u.get("overhead_cost_usd", 0) or 0)
        cost_out[c] = {**r, "total_cost_incl_overhead": round(total_incl, 6)}
        ac = "-" if r["cost_usd"] is None else f"{r['cost_usd']:.2f}"
        tc = f"{total_incl:.2f}"
        pq = "-" if r["usd_per_query"] is None else f"{r['usd_per_query']:.4f}"
        pc = "-" if r["usd_per_correct"] is None else f"{r['usd_per_correct']:.4f}"
        print(f"{c:<24}{pt+ct:>13,}{ac:>9}{tc:>9}{pq:>10}{pc:>11}")
    print("\n$/correct = cost to solve one task (the honest efficiency metric). '+ovhd' includes the "
          "gate/critic calls when a run was metered (else = actor).")

    out = {"overall": {c: _overall(scored[c]) for c in conds},
           "non_empty": {c: _overall(scored[c][scored[c]["query"].apply(lambda q: q not in empty_q)])
                         for c in conds} if empty_q else {},
           "cost": cost_out, "n_empty_gold": len(empty_q)}
    dest = os.path.join(exp_dir, "results", "crunch_summary.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(out, open(dest, "w"), indent=2)
    print(f"\nWrote {dest}")


if __name__ == "__main__":
    main()
