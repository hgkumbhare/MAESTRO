"""Done-query store — records which queries are already completed for a given run config.

Keyed by a *signature* of the params that affect results (experiment, condition, model,
agent_engine, temperature). Because the key is config-based (not shard-based), you can
stop a run and resume with a DIFFERENT number of shards — only undone queries re-run.

Stored value: the raw prediction rows (query, function_calls, full_response, error,
tool_set) so results can be re-scored uniformly against ground truth at merge time.

Flow:
  load_done / done_queries  -> what's already finished (skip these when sharding)
  patch_done                -> after a run, merge new predictions into the store
"""
import os
import re

import pandas as pd

from src.evals.constants import TEMPERATURE


def signature(config, condition):
    """Config signature that defines a unique (experiment, condition, params) run.

    Includes tool_set so improved-tools runs never collide with / reuse original-tools results.
    """
    parts = [
        config["experiment"], condition, config["model"],
        config.get("agent_engine", "langchain"),
        f"tools-{config.get('tool_set', 'original')}", f"temp{TEMPERATURE}",
    ]
    return re.sub(r"[^A-Za-z0-9_.-]", "-", "__".join(str(p) for p in parts))


def store_path(here, config, condition):
    d = os.path.join(here, "results", "done_store")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, signature(config, condition) + ".pkl")


def load_done(here, config, condition):
    """Return the stored prediction rows for this (config, condition), or an empty frame."""
    p = store_path(here, config, condition)
    return pd.read_pickle(p) if os.path.exists(p) else pd.DataFrame()


def done_queries(here, config, condition):
    """Set of query strings already completed for this (config, condition)."""
    df = load_done(here, config, condition)
    return set(df["query"].tolist()) if "query" in df.columns else set()


def patch_done(here, config, condition, new_preds):
    """Merge new prediction rows into the store (dedupe by query, keep newest). Returns merged."""
    old = load_done(here, config, condition)
    frames = [f for f in (old, new_preds) if f is not None and len(f)]
    if not frames:
        return old
    merged = pd.concat(frames, ignore_index=True).drop_duplicates(subset="query", keep="last")
    merged.to_pickle(store_path(here, config, condition))
    return merged


def seed_from(here, config, condition, src_here, src_config):
    """Copy completed predictions for `condition` from another experiment's store into this one.

    Use to reuse identical work across experiments (e.g. `base` is the same whether run under
    E1 or E1.5, since no skills are injected). Only valid when the params that affect results
    (model, agent_engine, temperature) match — which the signature enforces.
    """
    src = load_done(src_here, src_config, condition)
    if len(src):
        patch_done(here, config, condition, src)
    return len(src)
