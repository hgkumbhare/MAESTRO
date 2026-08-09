"""Run the E12 base and All arms on each dataset with Qwen 2.5 7B Instruct (OpenRouter).

All LLM components (actor, LLM gate, critic) use qwen-2.5-7b via OpenRouter with fast
provider routing (experiments/common/llm_client.py). Outputs are isolated under
``by_model/qwen-2.5-7b/<domain>/`` and are resumable.

Run:  python experiments/E12_abalation/run_qwen7b_base_all.py
      python experiments/E12_abalation/run_qwen7b_base_all.py analytics email   # subset
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

from experiments.common.parallel_runner import run_parallel

HERE = os.path.dirname(__file__)
QDIR = "data/processed/queries_and_answers"
MODEL = "qwen-2.5-7b"
DOMAINS = [
    "project_management",
    "analytics",
    "calendar",
    "customer_relationship_manager",
    "email",
    "multi_domain",
]
CONDITIONS = ["base", "skills_gated_verify_with_tool_dependency_skills"]


def config_for(domain: str) -> dict:
    return {
        "experiment": "E12_qwen7b_base_all",
        "status": "run",
        "model": MODEL,
        "queries_paths": [f"{QDIR}/{domain}_queries_and_answers.csv"],
        "conditions": CONDITIONS,
        "agent_engine": "smolagents",
        "seed": 42,
        "checkpoint_every": 25,
        "parallel": True,
        "max_workers": 4,
        "stagger_seconds": 8,
        "gating": {"method": "llm"},
        "tool_set": "improved",
        "verify": {"max_iters": 2, "critic_model": MODEL},
        "notes": f"E12 Qwen 2.5 7B base vs All on {domain}; actor+gate+critic all use {MODEL} via OpenRouter.",
    }


def main():
    wanted = sys.argv[1:] or DOMAINS
    unknown = [d for d in wanted if d not in DOMAINS]
    if unknown:
        raise SystemExit(f"Unknown domain(s): {unknown}. Known: {DOMAINS}")
    for domain in wanted:
        output_dir = os.path.join(HERE, "by_model", MODEL, domain)
        os.makedirs(output_dir, exist_ok=True)
        print(f"\n{'=' * 70}\n[E12 Qwen-7B] {domain}\n{'=' * 70}")
        run_parallel(output_dir, config_for(domain))


if __name__ == "__main__":
    main()
