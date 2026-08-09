"""E12 — run ONLY the `verify` arm (actor-critic alone, no skills) on project_management.

Isolated results tree (./by_domain/project_management_verify/) so it does NOT overwrite the
existing 8-arm PM metrics in ./results/. Merge the number into RESULTS.md afterward.

Run:  python experiments/E12_abalation/run_verify_pm.py
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

from experiments.common.parallel_runner import run_parallel

HERE = os.path.dirname(__file__)

CONFIG = {
    "experiment": "E12_abalation",
    "status": "run",
    "model": "gpt-4o-mini-2024-07-18",
    "queries_paths": [
        "data/processed/queries_and_answers/project_management_queries_and_answers.csv"
    ],
    "conditions": ["verify"],
    "agent_engine": "smolagents",
    "seed": 1,
    "checkpoint_every": 25,
    "parallel": True,
    "max_workers": 6,
    "stagger_seconds": 8,
    "gating": {"method": "llm"},
    "tool_set": "improved",
    "verify": {"max_iters": 2, "critic_model": "gpt-4o-mini-2024-07-18"},
    "notes": "verify arm only (actor-critic, no skills) on PM; isolated from the 8-arm run.",
}


def main():
    here_dir = os.path.join(HERE, "by_domain", "project_management_verify")
    os.makedirs(here_dir, exist_ok=True)
    print(f"[E12] verify-only on project_management -> {here_dir}")
    run_parallel(here_dir, CONFIG)


if __name__ == "__main__":
    main()
