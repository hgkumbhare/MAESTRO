"""Run E12 base and All arms with Qwen-2.5-72B via OpenRouter (price-sorted provider routing).
Actor + gate + critic all use qwen-2.5-72b. Outputs under by_model/qwen-2.5-72b/<domain>/.
Run:  python experiments/E12_abalation/run_qwen72b_base_all.py project_management analytics
"""
import os, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
from experiments.common.parallel_runner import run_parallel

HERE = os.path.dirname(__file__)
QDIR = "data/processed/queries_and_answers"
MODEL = "qwen-2.5-72b"
DOMAINS = ["project_management", "analytics", "calendar",
           "customer_relationship_manager", "email", "multi_domain"]
CONDITIONS = ["base", "skills_gated_verify_with_tool_dependency_skills"]


def config_for(domain: str) -> dict:
    return {
        "experiment": "E12_qwen72b_base_all", "status": "run", "model": MODEL,
        "queries_paths": [f"{QDIR}/{domain}_queries_and_answers.csv"],
        "conditions": list(CONDITIONS), "agent_engine": "smolagents",
        "seed": 42, "checkpoint_every": 25, "parallel": True,
        "max_workers": 4, "stagger_seconds": 8,
        "gating": {"method": "llm"}, "tool_set": "improved",
        "verify": {"max_iters": 2, "critic_model": MODEL},
        "notes": f"E12 Qwen-2.5-72B base vs All on {domain}; all LLM components via OpenRouter (price-sorted).",
    }


def main():
    wanted = sys.argv[1:] or DOMAINS
    unknown = [d for d in wanted if d not in DOMAINS]
    if unknown:
        raise SystemExit(f"Unknown domain(s): {unknown}. Known: {DOMAINS}")
    for domain in wanted:
        out = os.path.join(HERE, "by_model", MODEL, domain)
        os.makedirs(out, exist_ok=True)
        print(f"\n{'='*70}\n[E12 Qwen-2.5-72B] {domain}\n{'='*70}")
        run_parallel(out, config_for(domain))


if __name__ == "__main__":
    main()
