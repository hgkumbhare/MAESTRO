"""E12 — ablation across all conditions.

Runs every condition in experiments/common/conditions.py (base, integration-test,
tool-dependency-skills, skills, skills_gated, skills_gated_verify, and the combined
arm) on the PM queries and writes per-query CSVs + metrics.json.

Run:  python experiments/E12_abalation_only_pm/run.py
"""
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

from experiments.common.runner import run_experiment
from experiments.common.parallel_runner import run_parallel

HERE = os.path.dirname(__file__)


def main():
    with open(os.path.join(HERE, "config.json")) as f:
        config = json.load(f)
    print(f"[{config['experiment']}] conditions={config['conditions']} tool_set={config.get('tool_set')}")
    if config.get("parallel") and config.get("queries_paths"):
        run_parallel(HERE, config)
    else:
        run_experiment(HERE, config)


if __name__ == "__main__":
    main()
