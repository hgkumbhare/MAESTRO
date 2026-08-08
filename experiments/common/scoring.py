"""Scoring utilities shared across experiments.

Wraps the repo's own `is_correct` (outcome-based: execute predicted vs ground-truth tool
calls, compare DB state) and adds the covered/uncovered split and per-domain breakdown.
"""
import ast

import pandas as pd

from src.evals.utils import is_correct, has_side_effects
from experiments.common.coverage import coverage


def _first_domain(domains_cell) -> str:
    """Parse a queries-CSV 'domains' cell like "['project_management']" -> 'project_management'."""
    try:
        val = ast.literal_eval(domains_cell) if isinstance(domains_cell, str) else domains_cell
        if isinstance(val, (list, tuple)) and val:
            return str(val[0])
        return str(val)
    except Exception:
        return str(domains_cell)


def score(preds_df: pd.DataFrame, gt_df: pd.DataFrame) -> pd.DataFrame:
    """Join predictions to ground truth and compute per-query correctness + tags.

    preds_df: from generate_results (must have columns 'query', 'function_calls', 'error').
    gt_df:    queries-and-answers CSV loaded with 'answer' still as a string; parsed here.
    Returns one row per query with: correct (bool), coverage (covered/uncovered), domain.
    """
    gt = gt_df.copy()
    if gt["answer"].dtype == object and isinstance(gt["answer"].iloc[0], str):
        gt["answer"] = gt["answer"].apply(ast.literal_eval)

    preds = preds_df.rename(columns={"function_calls": "prediction"}).fillna("")
    df = preds.merge(gt.rename(columns={"answer": "ground_truth"}), on="query")

    df["prediction"] = df["prediction"].apply(lambda a: [x.replace("\n", "\\n") for x in a])
    df["ground_truth"] = df["ground_truth"].apply(lambda a: [x.replace("\n", "\\n") for x in a])
    df["correct"] = [
        is_correct(p, g, e) for p, g, e in zip(df["prediction"], df["ground_truth"], df["error"])
    ]
    df["unwanted_side_effects"] = [
        has_side_effects(p, g) for p, g in zip(df["prediction"], df["ground_truth"])
    ]
    if "base_template" in df.columns:
        df["coverage"] = df["base_template"].apply(coverage)
    # Prefer an explicit source_domain tag (set when sharding mixes domains); else parse 'domains'.
    if "source_domain" in df.columns:
        df["domain"] = df["source_domain"]
    elif "domains" in df.columns:
        df["domain"] = df["domains"].apply(_first_domain)
    return df


def split_summary(df: pd.DataFrame) -> dict:
    """Accuracy for covered / uncovered / all groups (requires a 'coverage' column)."""
    out = {}
    for grp in ["covered", "uncovered", "all"]:
        sub = df if grp == "all" else df[df["coverage"] == grp]
        out[grp] = {"n": int(len(sub)), "accuracy": float(100.0 * sub["correct"].mean()) if len(sub) else None}
    return out


def per_domain(df: pd.DataFrame) -> dict:
    """Accuracy per domain (requires a 'domain' column)."""
    out = {}
    for dom, sub in df.groupby("domain"):
        out[str(dom)] = {"n": int(len(sub)), "accuracy": float(100.0 * sub["correct"].mean())}
    return out


def _agg(sub: pd.DataFrame) -> dict:
    """Accuracy + side-effect rate for a subset."""
    if not len(sub):
        return {"n": 0, "accuracy": None, "side_effect_rate": None}
    return {
        "n": int(len(sub)),
        "accuracy": float(100.0 * sub["correct"].mean()),
        "side_effect_rate": float(100.0 * sub["unwanted_side_effects"].mean())
        if "unwanted_side_effects" in sub.columns else None,
    }


def to_records(scored: dict, experiment: str, model: str, seed: int = 1,
               coverage_split: bool = False) -> list:
    """Emit the tidy reporting schema (docs/reporting_standard.md §3): one row per cell.

    `scored` = {condition_name: scored_df}. By default emits the **overall** accuracy per
    (condition, domain) — grain 'domain'. Set coverage_split=True to ALSO emit the
    covered/uncovered breakdown (leakage guardrail; only meaningful for the leaky method —
    skills apply to both equally). delta_vs_base is filled against 'base' on the matching
    (domain, split).
    """
    # 1. gather raw cells
    cells = []  # (condition, domain, grain, split, agg)
    for cond, df in scored.items():
        domains = sorted(df["domain"].unique()) if "domain" in df.columns else [None]
        for dom in domains:
            dsub = df if dom is None else df[df["domain"] == dom]
            if coverage_split and "coverage" in dsub.columns and dsub["coverage"].notna().any():
                for split in ["covered", "uncovered"]:
                    cells.append((cond, dom, "template", split, _agg(dsub[dsub["coverage"] == split])))
            # overall per domain (the default headline)
            cells.append((cond, dom, "domain", "all", _agg(dsub)))

    # 2. base lookup for deltas
    base_acc = {
        (dom, split): agg["accuracy"]
        for (cond, dom, grain, split, agg) in cells if cond == "base"
    }

    # 3. assemble records
    records = []
    for cond, dom, grain, split, agg in cells:
        b = base_acc.get((dom, split))
        delta = None if (agg["accuracy"] is None or b is None or cond == "base") else round(agg["accuracy"] - b, 1)
        records.append({
            "experiment": experiment, "model": model, "seed": seed,
            "condition": cond, "domain": dom, "split_grain": grain, "split": split,
            "n": agg["n"], "accuracy": None if agg["accuracy"] is None else round(agg["accuracy"], 1),
            "side_effect_rate": None if agg["side_effect_rate"] is None else round(agg["side_effect_rate"], 1),
            "delta_vs_base": delta,
        })
    return records


def standard_table(records: list) -> str:
    """Render the canonical display table (docs/reporting_standard.md §6) from tidy records."""
    hdr = f"{'condition':<14}{'domain':<22}{'split (grain)':<22}{'n':>4}{'acc%':>8}{'Δbase':>8}{'side%':>8}"
    lines = [hdr, "-" * len(hdr)]
    for r in records:
        acc = "-" if r["accuracy"] is None else f"{r['accuracy']:.1f}"
        dlt = "-" if r["delta_vs_base"] is None else f"{r['delta_vs_base']:+.1f}"
        se = "-" if r["side_effect_rate"] is None else f"{r['side_effect_rate']:.1f}"
        sp = f"{r['split']} ({r['split_grain']})"
        lines.append(f"{r['condition']:<14}{str(r['domain']):<22}{sp:<22}{r['n']:>4}{acc:>8}{dlt:>8}{se:>8}")
    return "\n".join(lines)


def compare_conditions(scored: dict) -> str:
    """Pretty covered/uncovered table across conditions. `scored` = {condition_name: df}."""
    names = list(scored.keys())
    lines = [f"{'group':<10}" + "".join(f"{n:>14}" for n in names)]
    for grp in ["covered", "uncovered", "all"]:
        cells = []
        for n in names:
            s = split_summary(scored[n])[grp]
            cells.append("-" if s["accuracy"] is None else f"{s['accuracy']:.1f}")
        lines.append(f"{grp:<10}" + "".join(f"{c:>14}" for c in cells))
    return "\n".join(lines)
