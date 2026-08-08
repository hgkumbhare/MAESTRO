"""Critic for the actor-critic verify-and-correct mechanism (E1.8).

make_critic(model) -> critic(query, function_calls, response) -> (ok: bool, feedback: str).

The critic reasons about TASK-SATISFACTION from the query + the agent's own trace only. It NEVER
sees the ground-truth answer (that would be test-set access). On fail it returns one specific,
actionable instruction so the actor can correct.
"""
import os

_client = None


def _openai():
    global _client
    if _client is None:
        from openai import OpenAI
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        key = open(os.path.join(repo, "openai_key.txt")).read().strip()
        _client = OpenAI(api_key=key)
    return _client


def _format_trace(trace_items, max_out=300):
    """Render each tool call WITH its observation (output) for the critic."""
    lines = []
    for it in trace_items:
        name = it.get("function_name", "")
        params = it.get("parameters", {})
        args = ", ".join(f"{k}={v!r}" for k, v in params.items()) if isinstance(params, dict) else ""
        out = str(it.get("output"))
        if len(out) > max_out:
            out = out[:max_out] + " …(truncated)"
        lines.append(f"{name}({args})\n    -> {out}")
    return "\n".join(lines) if lines else "(no tool calls made)"


_PROMPT = """Task: "{query}"

The agent made these tool calls, each shown with the result it returned:
{calls}

The agent's final answer: {response}

Judge ONLY whether the trace plausibly and completely satisfies the task. Do not assume you know
the correct answer. Work through these checks in order.

CHECK 1 — claimed vs actually done. Take each action verb in the final answer (created, deleted,
sent, updated, assigned, replied, forwarded, ...) and find the specific tool call in the trace above
that performed it. If ANY claimed action has no corresponding tool call in the trace, that is a FAIL
— the agent hallucinated doing work it never did. A trace that only searched/looked up but then
claims it created or changed something is a FAIL.

CHECK 2 — conditional tasks ("if X ... then ..."). The agent must FIRST verify condition X from a tool
output, THEN act only if it holds. FAIL if it acted without a tool call that checks the condition, or
if it acted despite the condition being false.

CHECK 3 — right target. FAIL if it acted on the wrong set of records (all of them, or the wrong ones)
instead of exactly what the task specifies. If the task NAMES a specific record (e.g. "the meeting
titled X") and the search for it returned nothing, FAIL — but the fix is to search that exact name,
not to broaden indiscriminately.

CHECK 4 — empty results are often CORRECT, do not manufacture failures. A well-specified search that
returns nothing, on a task whose answer may legitimately be "none / do nothing", is usually the RIGHT
answer. NEVER tell the agent to loosen a filter or "broaden and retry" just because a search returned
nothing, unless CHECK 3 applies (a specifically-named record that must exist). Doing nothing when the
condition isn't met is a PASS, not a failure.

Reply EXACTLY "PASS" if all checks are satisfied — INCLUDING when the correct outcome is to do nothing
or return an empty result.
Otherwise reply "FAIL: <one specific, actionable instruction telling the agent how to fix it>"."""


def make_critic(model="gpt-4o-mini-2024-07-18"):
    from src.evals.constants import SEED

    def critic(query, trace_items, response):
        calls = _format_trace(trace_items)
        prompt = _PROMPT.format(query=query, calls=calls, response=response)
        try:
            r = _openai().chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}],
                temperature=0, seed=SEED, max_tokens=120)
            t = (r.choices[0].message.content or "").strip()
            try:
                from experiments.common.usage_meter import record
                record("critic", model, getattr(r.usage, "prompt_tokens", 0),
                       getattr(r.usage, "completion_tokens", 0))
            except Exception:
                pass
        except Exception:
            return True, ""  # critic failure -> accept (don't block the pipeline)
        if t.upper().startswith("PASS"):
            return True, ""
        fb = t.split(":", 1)[1].strip() if ":" in t else t
        return False, fb

    return critic
