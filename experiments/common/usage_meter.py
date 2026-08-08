"""Process-global token meter for the OVERHEAD calls that bypass the litellm callback.

The actor's tokens are captured by litellm/langchain callbacks in the runner. But three helper
calls go straight through the OpenAI client and are invisible to those callbacks:
  - the embedding gate            (triggers._embed)          tag "gate_embed"
  - the LLM skill-selection gate  (triggers.fired_skills_llm) tag "gate_llm"
  - the actor-critic critic        (critic.critic)            tag "critic"

Each of those call sites calls record(...) after its API response. The runner snapshots totals()
before/after each condition's fresh work and folds the delta into that condition's usage, so
metrics.json reflects the TRUE cost (actor + overhead), not just the actor.

Global, so it works across the sequential runner (reset per condition via before/after deltas) and
each parallel shard process (its own meter → its own metrics.json → summed at merge).
"""
import threading

_lock = threading.Lock()
# (tag, model) -> {"prompt_tokens", "completion_tokens", "calls"}
_METER = {}


def record(tag, model, prompt_tokens=0, completion_tokens=0):
    """Add one overhead call's usage. Never raises (metering must not break inference)."""
    try:
        with _lock:
            k = (tag, model)
            e = _METER.setdefault(k, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
            e["prompt_tokens"] += int(prompt_tokens or 0)
            e["completion_tokens"] += int(completion_tokens or 0)
            e["calls"] += 1
    except Exception:
        pass


def totals():
    """Snapshot of cumulative overhead so far: {(tag, model): {...}} plus flat token sums."""
    with _lock:
        by = {f"{t}|{m}": dict(v) for (t, m), v in _METER.items()}
    pt = sum(v["prompt_tokens"] for v in by.values())
    ct = sum(v["completion_tokens"] for v in by.values())
    calls = sum(v["calls"] for v in by.values())
    return {"by_tag": by, "prompt_tokens": pt, "completion_tokens": ct, "calls": calls}


def delta(before, after):
    """Overhead accrued between two totals() snapshots, incl. per-(tag,model) breakdown + $ cost."""
    from experiments.common.pricing import cost_usd
    keys = set(before["by_tag"]) | set(after["by_tag"])
    by = {}
    tot_cost = 0.0
    for k in keys:
        b = before["by_tag"].get(k, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        a = after["by_tag"].get(k, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        dp = a["prompt_tokens"] - b["prompt_tokens"]
        dc = a["completion_tokens"] - b["completion_tokens"]
        dn = a["calls"] - b["calls"]
        if dp or dc or dn:
            model = k.split("|", 1)[1]
            c = cost_usd(model, dp, dc) or 0.0
            tot_cost += c
            by[k] = {"prompt_tokens": dp, "completion_tokens": dc, "calls": dn, "cost_usd": round(c, 6)}
    return {
        "overhead_prompt_tokens": after["prompt_tokens"] - before["prompt_tokens"],
        "overhead_completion_tokens": after["completion_tokens"] - before["completion_tokens"],
        "overhead_calls": after["calls"] - before["calls"],
        "overhead_cost_usd": round(tot_cost, 6),
        "overhead_by_tag": by,
    }


def reset():
    with _lock:
        _METER.clear()
