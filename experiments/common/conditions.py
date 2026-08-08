"""Condition builders — the treatments compared across experiments.

Each condition is a thin wrapper over the repo's `generate_results`, so every experiment
runs the *same* inference path with only the treatment varying.

- base      : original tool set, no examples/tests             (control)
- improved  : rewritten tool descriptions + integration tests  (the current, leaky method)
- skills    : original tools + injected leakage-safe skill cards (E1) — via
              generate_results(extra_system_prompt=render_skills(...))
"""
from src.evals.utils import generate_results
from experiments.common.skills import render_skills

# tool_set is a RUN-LEVEL knob (from config), NOT per-condition — all conditions in a run share
# the same tool descriptions (team standard = "improved"). Conditions vary only:
#   include_integration_tests : the LEAKY integration tests (E0/S3) — only the 'improved' arm uses them
#   skills : "none" | "all" (always-on, E1) | "gated" (trigger-gated per query, E1.5)
CONDITIONS = {
    "base": dict(include_integration_tests=False, skills="none", verify=False),
    "improved": dict(include_integration_tests=True, skills="none", verify=False),  # + leaky tests (E0)
    "skills": dict(include_integration_tests=False, skills="all", verify=False),
    "skills_gated": dict(include_integration_tests=False, skills="gated", verify=False),
    # actor-critic verify-and-correct on top of gated skills (E1.8)
    "skills_gated_verify": dict(include_integration_tests=False, skills="gated", verify=True),
}


def run_condition(name: str, queries_path: str, model: str, tool_selection: str = "all",
                  agent_engine: str = "langchain", tool_set: str = "original",
                  include_demo: bool = False,
                  gate_threshold: float = 0.35, gate_method: str = "embedding",
                  verify_cfg: dict = None):
    """Run one condition and return the predictions DataFrame (as generate_results returns).

    include_demo: also render each card's held-out micro-demo (E2 grounding).
    gate_threshold / gate_method: trigger-gate config for skills_gated
      (method 'embedding' = cosine+threshold / E1.5; 'llm' = classifier call / E1.5.5).
    """
    if name not in CONDITIONS:
        raise ValueError(f"Unknown condition '{name}'. Known: {list(CONDITIONS)}")
    cfg = CONDITIONS[name]

    if cfg["skills"] == "all":
        extra = render_skills(include_demo=include_demo) + "\n\n"
    elif cfg["skills"] == "gated":
        from experiments.common.triggers import render_gated_skills

        def extra(query):  # per-query: inject only the skills whose trigger fires
            block = render_gated_skills(query, method=gate_method, threshold=gate_threshold,
                                        model=model, include_demo=include_demo)
            return (block + "\n\n") if block else ""
    else:
        extra = ""

    verify = None
    if cfg.get("verify"):
        from experiments.common.critic import make_critic
        vc = verify_cfg or {}
        verify = {"max_iters": vc.get("max_iters", 2),
                  "critic": make_critic(vc.get("critic_model", model))}

    return generate_results(
        queries_path, model,
        tool_selection=tool_selection,
        agent_engine=agent_engine,
        tool_set=tool_set,
        include_integration_tests=cfg["include_integration_tests"],
        extra_system_prompt=extra,
        verify=verify,
    )
