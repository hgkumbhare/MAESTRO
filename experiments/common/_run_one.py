"""Subprocess entry point for one parallel unit (a single domain).

Called by parallel_runner as: python experiments/common/_run_one.py <domain_dir>
Reads <domain_dir>/config.json and runs the sequential runner there.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from experiments.common.runner import run_experiment  # noqa: E402

if __name__ == "__main__":
    here = sys.argv[1]
    with open(os.path.join(here, "config.json")) as f:
        cfg = json.load(f)
    run_experiment(here, cfg)
