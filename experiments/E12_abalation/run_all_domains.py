"""E12 — ablation across NON-PM domains, one isolated run per dataset.

Runs the five requested arms on every domain EXCEPT project_management (PM already
lives in ./results/metrics.json from run.py). Each domain gets its own results tree
under ./by_domain/<domain>/results/ so token/cost usage is tracked PER DATASET
(needed for the "cost per task per dataset" table in RESULTS.md).

Arms:
  base                                             — control
  with_tool_dependency_skills                      — tool dependency
  skills_gated                                     — gated skills
  verify                                           — actor-critic alone (critic on base, no skills)
  skills_gated_verify_with_tool_dependency_skills  — all (tool dep + gated + critic)

Run:  python experiments/E12_abalation/run_all_domains.py
      python experiments/E12_abalation/run_all_domains.py analytics email   # subset
Resumable: re-running only re-does not-yet-done (condition, query) pairs.
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

from experiments.common.parallel_runner import run_parallel

HERE = os.path.dirname(__file__)
QDIR = "data/processed/queries_and_answers"

# All datasets except project_management (PM is the existing ./results run).
DOMAINS = [
    "analytics",
    "calendar",
    "customer_relationship_manager",
    "email",
    "multi_domain",
]

CONDITIONS = [
    "base",
    "with_tool_dependency_skills",
    "skills_gated",
    "verify",
    "skills_gated_verify_with_tool_dependency_skills",
]


def config_for(domain: str) -> dict:
    return {
        "experiment": "E12_abalation",
        "status": "run",
        "model": "gpt-4o-mini-2024-07-18",
        "queries_paths": [f"{QDIR}/{domain}_queries_and_answers.csv"],
        "conditions": list(CONDITIONS),
        "agent_engine": "smolagents",
        "seed": 1,
        "checkpoint_every": 25,
        "parallel": True,
        "max_workers": 6,
        "stagger_seconds": 8,
        "gating": {"method": "llm"},
        "tool_set": "improved",
        "verify": {"max_iters": 2, "critic_model": "gpt-4o-mini-2024-07-18"},
        "notes": f"E12 ablation on {domain} (isolated run for per-dataset cost).",
    }


def main():
    wanted = sys.argv[1:] or DOMAINS
    unknown = [d for d in wanted if d not in DOMAINS]
    if unknown:
        raise SystemExit(f"Unknown domain(s) {unknown}. Known: {DOMAINS}")
    for domain in wanted:
        here_domain = os.path.join(HERE, "by_domain", domain)
        os.makedirs(here_domain, exist_ok=True)
        cfg = config_for(domain)
        print(f"\n{'='*70}\n[E12] domain={domain}  conditions={cfg['conditions']}\n{'='*70}")
        run_parallel(here_domain, cfg)


if __name__ == "__main__":
    main()
