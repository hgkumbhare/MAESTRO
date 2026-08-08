"""Trigger-gated skill selection (E1.5) — inject only the skills whose Trigger matches a query.

Domain-agnostic by construction: the gate scores the QUERY TEXT against each skill's `Trigger`
via embedding cosine similarity. It never sees the domain, gold answer, or template (gating by
domain would be leakage). Threshold is fixed a priori (not tuned on the test set).

Uses OpenAI embeddings (text-embedding-3-small) — separate rate-limit bucket from the chat model,
so it doesn't compete with the run's TPM. Query with no matching trigger → empty skills block.
"""
import math
import os

from experiments.common.skills import SKILL_CARDS, render_skill

_client = None
_trig_emb = None
_EMBED_MODEL = "text-embedding-3-small"


def _openai():
    global _client
    if _client is None:
        from openai import OpenAI
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        key = open(os.path.join(repo, "openai_key.txt")).read().strip()
        _client = OpenAI(api_key=key)
    return _client


def _embed(texts):
    r = _openai().embeddings.create(model=_EMBED_MODEL, input=texts)
    try:
        from experiments.common.usage_meter import record
        record("gate_embed", _EMBED_MODEL, getattr(r.usage, "prompt_tokens", 0), 0)
    except Exception:
        pass
    return [d.embedding for d in r.data]


def _trigger_embeddings():
    global _trig_emb
    if _trig_emb is None:
        _trig_emb = _embed([c["trigger"] for c in SKILL_CARDS])
    return _trig_emb


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def trigger_scores(query):
    """Return [(skill_card, cosine_sim), ...] for the query against every trigger."""
    qe = _embed([query])[0]
    return [(SKILL_CARDS[i], _cos(qe, t)) for i, t in enumerate(_trigger_embeddings())]


def fired_skills(query, threshold=0.35):
    """EMBEDDING gate: skill cards whose Trigger matches the query (cosine >= threshold)."""
    return [c for c, s in trigger_scores(query) if s >= threshold]


def fired_skills_llm(query, model="gpt-4o-mini-2024-07-18"):
    """LLM gate: one focused classification call — which skills genuinely apply to this task?

    No threshold to tune (avoids the eval-tuning leakage of the embedding gate) and judges
    semantics the query→trigger embedding misses (e.g. delete-meeting needs search-then-delete).
    """
    lines = "\n".join(f"- {c['id']}: {c['trigger']}" for c in SKILL_CARDS)
    ids = ", ".join(c["id"] for c in SKILL_CARDS)
    prompt = (
        f'A tool-using agent must complete this task:\n"{query}"\n\n'
        "Below are tool-use skills, each 'id: trigger'. Return the exact ID STRINGS "
        "(not numbers) of the skills whose trigger applies to THIS task, comma-separated. "
        f'If none apply, return "none". Do not explain.\nValid ids: {ids}\n\n' + lines
    )
    from src.evals.constants import SEED
    from experiments.common.llm_client import chat_client_and_model, chat_kwargs
    client, model_id = chat_client_and_model(model)  # gpt-* -> OpenAI, llama/qwen -> OpenRouter
    # The gate call can fail transiently (budget OpenRouter providers 429/400/return
    # choices=None). Retry a few times, then fall back to "no skill fired" so a flaky
    # provider degrades a single query rather than crashing the whole run.
    r = None
    for _attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=model_id, messages=[{"role": "user", "content": prompt}],
                temperature=0, seed=SEED, max_tokens=60, **chat_kwargs(model))
            break
        except Exception:
            r = None
    if r is None:
        return []
    try:
        from experiments.common.usage_meter import record
        record("gate_llm", model, getattr(r.usage, "prompt_tokens", 0),
               getattr(r.usage, "completion_tokens", 0))
    except Exception:
        pass
    choices = getattr(r, "choices", None) or []
    text = ((choices[0].message.content if choices else "") or "").lower()
    return [c for c in SKILL_CARDS if c["id"].lower() in text]


def render_gated_skills(query, method="embedding", threshold=0.35,
                        model="gpt-4o-mini-2024-07-18", include_demo=False):
    """System-level gate: render ONLY the fired skills (empty string if none fire).

    method: 'embedding' (cosine vs trigger, E1.5) or 'llm' (classifier call, E1.5.5).
    """
    fired = fired_skills_llm(query, model) if method == "llm" else fired_skills(query, threshold)
    if not fired:
        return ""
    header = "Tool-interaction skills relevant to this task:\n\n"
    return header + "\n\n".join(render_skill(c, include_demo) for c in fired)
