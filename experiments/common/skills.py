"""Leakage-safe tool-interaction skill cards (Q3 injectable unit).

Each card is DATASET-AGNOSTIC: it teaches a tool-use pattern via triggers on parameter
*semantics* (e.g. "a param that is an identifier"), never via eval entities or templates.
Because they contain no eval-specific content, they are leakage-safe by construction
(docs/retrieval_design.md §10). E1 injects the rendered block into the ReAct system prompt.

`micro_demo` is an OPTIONAL grounding example (E2) using held-out sandbox entities only
(experiments.common.sandbox). Leave "" to run skills-only (E1).
"""

SKILL_CARDS = [
    {
        "id": "identifier-resolution",
        "failure_modes": ["fabricated-params", "wrong-tool-selection"],
        "trigger": "The task refers to a person or entity by NAME, but the tools operate on their email or id — so the identifier must be looked up before you can act on that person's records.",
        "procedure": [
            "First call the lookup tool to resolve the identifier.",
            "Pass the EXACT returned value to the next tool.",
            "Never fabricate or guess an id/email.",
        ],
        "rationale": "Fabricated identifiers are the most common parameter hallucination.",
        "applies_to": "Any tool whose params include *_email, *_id, assigned_to_*.",
        "micro_demo": "",
    },
    {
        "id": "reuse-returned-value",
        "failure_modes": ["stale-args", "fabricated-params"],
        "trigger": "The task requires feeding a value RETURNED by one tool call as the argument to a LATER tool call (a data dependency between two calls).",
        "procedure": [
            "Copy the returned value verbatim into the next call.",
            "Do not paraphrase, reformat, or re-derive it.",
        ],
        "rationale": "Re-deriving values instead of reusing them introduces mismatches.",
        "applies_to": "Any multi-step chain where tool B consumes tool A's output.",
        "micro_demo": "",
    },
    {
        "id": "no-duplicate-calls",
        "failure_modes": ["duplicate-calls"],
        "trigger": "The task involves MULTIPLE steps that would otherwise re-fetch information already retrieved earlier in the same task.",
        "procedure": [
            "Reuse the result you already obtained.",
            "Do not call the same tool again with the same arguments.",
        ],
        "rationale": "Redundant calls waste steps and can cause inconsistent state.",
        "applies_to": "Read tools (search_*, get_*_information_by_id).",
        "micro_demo": "",
    },
    {
        "id": "fetch-before-act",
        "failure_modes": ["fabricated-params", "wrong-sequence"],
        "trigger": "The task asks you to MODIFY or DELETE a specific record, but you must first search/look it up to obtain its id or current fields.",
        "procedure": [
            "Search/look up the target first to obtain its id and current fields.",
            "Only then call the mutating tool with the retrieved id.",
        ],
        "rationale": "Acting before fetching leads to fabricated ids and wrong targets.",
        "applies_to": "Side-effecting tools (update_*, delete_*, create_*).",
        "micro_demo": "",
    },
    {
        "id": "right-tool-selection",
        "failure_modes": ["irrelevant-tool", "non-existent-tool"],
        "trigger": "The task plausibly maps to SEVERAL similar-looking tools where choosing the wrong one would silently return the wrong result.",
        "procedure": [
            "Pick the tool whose name and parameters match the task's intent.",
            "Only use tools that are listed; never invent a tool name.",
        ],
        "rationale": "Wrong or invented tools break the whole chain.",
        "applies_to": "All tools.",
        "micro_demo": "",
    },
    {
        "id": "read-output",
        "failure_modes": ["ignores-output"],
        "trigger": "The task's next action DEPENDS on the output of a prior tool call — e.g. conditional on a returned count/value, or iterating over the rows a search returned.",
        "procedure": [
            "Read the returned value and base the next action on it.",
            "If it returns multiple items, handle each as required.",
        ],
        "rationale": "Ignoring tool output causes confident-but-wrong final answers.",
        "applies_to": "All read tools feeding a subsequent decision.",
        "micro_demo": "",
    },
    {
        "id": "parameter-completeness",
        "failure_modes": ["omitted-params"],
        "trigger": "The task specifies constraints on WHICH records to act on (a status like 'in progress', a list/board, a date range, a product) that must be passed as filters to the search/query tool.",
        "procedure": [
            "Map EVERY constraint stated in the task into the matching search argument (status/list_name, board, due_date, product, etc.).",
            "Do NOT search by identity alone and then act on all results — filter to exactly what the task specifies. If the filtered search returns nothing, do nothing.",
        ],
        "rationale": "Omitting a stated filter returns too many records and causes wrong or excess mutations.",
        "applies_to": "Search/query tools with multiple optional filters (search_tasks, search_emails, search_customers, search_events).",
        "micro_demo": "",
    },
    {
        "id": "tool-required",
        "failure_modes": ["no-tool-when-required"],
        "trigger": "The task asks you to actually PERFORM a state change (create / update / delete / send), where it would be tempting to claim success without executing the tool.",
        "procedure": [
            "Execute the mutating tool; do not report the action as done until it succeeds.",
            "Do not fabricate a confirmation.",
        ],
        "rationale": "Claiming a state change happened without calling the tool is the core tool-bypass hallucination.",
        "applies_to": "State-changing tools (create_*, update_*, delete_*, send_*).",
        "micro_demo": "",
    },
]


def render_skill(card: dict, include_demo: bool = False) -> str:
    proc = "\n".join(f"  {i}. {step}" for i, step in enumerate(card["procedure"], 1))
    block = (
        f"SKILL: {card['id']}\n"
        f"Trigger: {card['trigger']}\n"
        f"Procedure:\n{proc}\n"
        f"Rationale: {card['rationale']}\n"
        f"Applies to: {card['applies_to']}"
    )
    if include_demo and card.get("micro_demo"):
        block += f"\nExample:\n{card['micro_demo']}"
    return block


def render_skills(cards=None, include_demo: bool = False) -> str:
    """Render the full skill block for injection into the system prompt."""
    cards = cards or SKILL_CARDS
    header = (
        "Tool-interaction skills (general rules for calling tools correctly). "
        "Apply the ones whose Trigger matches the task:\n\n"
    )
    return header + "\n\n".join(render_skill(c, include_demo) for c in cards)
