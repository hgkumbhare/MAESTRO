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
        "trigger": "The task names a person/entity, but the tool you need takes an email or id.",
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
        "trigger": "A value produced by one tool is needed as input to another.",
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
        "trigger": "You already have the result of a tool call.",
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
        "trigger": "A mutating tool needs an id/field you do not yet have.",
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
        "trigger": "Several tools look similar, or you are unsure a tool exists.",
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
        "trigger": "A tool returned data you need to decide the next step.",
        "procedure": [
            "Read the returned value and base the next action on it.",
            "If it returns multiple items, handle each as required.",
        ],
        "rationale": "Ignoring tool output causes confident-but-wrong final answers.",
        "applies_to": "All read tools feeding a subsequent decision.",
        "micro_demo": "",
    },
    {
        "id": "tool-required",
        "failure_modes": ["no-tool-when-required"],
        "trigger": "The task asks to change or retrieve real data.",
        "procedure": [
            "Do not answer from assumption; call the appropriate tool.",
            "Only claim an action is done after the tool call succeeds.",
        ],
        "rationale": "Answering without a tool call is the core tool-bypass hallucination.",
        "applies_to": "Any task requiring real data or a state change.",
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
