# Prompt structure — where skills are injected

How the prompt is assembled per query, and exactly where the skill text goes. Concrete
renders below are the real strings (smolagents / gpt-4o-mini, temp 0).

---

## Two layers
Every query the model sees is built from two parts:

1. **The agent's own system prompt** — smolagents' `CodeAgent` template
   (`smolagents/prompts/code_agent.yaml`). We do **not** touch this. It contains:
   - role ("expert assistant who solves tasks using code blobs")
   - the Thought → Code → Observation cycle instructions
   - a few worked few-shot examples
   - **the tool list with descriptions** (all 27 WorkBench tools) rendered into the template
   - code-format rules and the `final_answer` requirement

2. **The task message** — what we pass to `agent.run(task)`. **This is the part we
   control**, and it is where skills are injected. It is assembled as:

   ```
   [ SKILL BLOCK (may be empty) ] + [ date/constraints line ] + "\n" + [ the query ]
   ```

So the skill block sits at the **top of the task/user message**, before the date line
and the query. (For the langchain engine it's prepended to the *system* message instead;
smolagents puts it at the top of the task.)

Code path: `conditions.run_condition` builds `extra_system_prompt` (string for `skills`,
per-query callable for `skills_gated`) → `generate_results` computes `esp` per query and
does `prompt_template = esp + date_line`, then `agent.run(prompt_template + "\n" + query)`
([src/evals/utils.py](../src/evals/utils.py), the per-query loop).

---

## Assembly diagram
```
┌─────────────────────────── what the LLM sees ───────────────────────────┐
│ SYSTEM  (smolagents CodeAgent template — untouched)                       │
│   role + Thought/Code/Observation cycle + few-shot examples              │
│   + ALL 27 tool descriptions + code rules + final_answer                 │
├──────────────────────────────────────────────────────────────────────────┤
│ TASK  (what we pass to agent.run — WE control this)                       │
│   ┌────────────────────────────────────────────────────────────┐        │
│   │ SKILL BLOCK   ← injected here (empty / all-7 / gated subset) │        │
│   └────────────────────────────────────────────────────────────┘        │
│   Today's date is Thursday, 2023-11-30 ... (date + constraints)          │
│   <the query>                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## The three conditions — concrete skill blocks

### `base` — no skill block
The task is just the date line + query. `esp = ""`.
```
Today's date is Thursday, 2023-11-30 ... Meetings must not start before 9am ...
Reassign all of Yuki's in-progress tasks to Carlos
```

### `skills` (E1, always-on) — all 7 cards, every query
`esp = render_skills()`. Header tells the model to self-select (it doesn't, reliably):
```
Tool-interaction skills (general rules for calling tools correctly). Apply the ones
whose Trigger matches the task:

SKILL: identifier-resolution
Trigger: The task refers to a person or entity by NAME, but the tools operate on their
  email or id — so the identifier must be looked up before you can act ...
Procedure:
  1. First call the lookup tool to resolve the identifier.
  2. Pass the EXACT returned value to the next tool.
  3. Never fabricate or guess an id/email.
Rationale: Fabricated identifiers are the most common parameter hallucination.
Applies to: Any tool whose params include *_email, *_id, assigned_to_*.

SKILL: reuse-returned-value ...
SKILL: no-duplicate-calls ...        ← all 7 cards, regardless of the query
... (7 cards total, ~1.5k tokens)
```
This is what perturbed flat CRM/analytics queries in E1 (irrelevant cards still in context).

### `skills_gated` (E1.5.5) — only the skills whose trigger fires
`esp = render_gated_skills(query)` — an **LLM classifier** picks which cards apply.

**Chained query** `"Reassign all of Yuki's in-progress tasks to Carlos"` → 3 cards:
```
Tool-interaction skills relevant to this task:

SKILL: identifier-resolution ...   (resolve Yuki/Carlos → emails)
SKILL: fetch-before-act ...         (search tasks before updating)
SKILL: tool-required ...            (actually perform the update)
```

**Flat query** `"How many customers have status Proposal?"` → **empty string** (0 cards):
```
(no skill block — the task is just the date line + query, identical to `base`)
```
→ flat-query domains get zero skill noise (the fix for the E1 regressions).

---

## Key points
- Skills go in the **task message**, on top of the date line + query — *not* in the
  agent's system prompt (smolagents) / *in* the system prompt (langchain).
- The **27 tool descriptions live in the agent's system prompt**, re-sent every step —
  this is the bulk of the token cost, independent of skills.
- `base` and a flat-query `skills_gated` produce an **identical task** (no skill block) —
  which is exactly why gating should remove the flat-domain regressions.
- Renders/logic: `experiments/common/skills.py` (cards + `render_skills`),
  `experiments/common/triggers.py` (`render_gated_skills`, the gate),
  `experiments/common/conditions.py` (builds `extra_system_prompt`).
