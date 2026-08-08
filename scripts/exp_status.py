"""Progress for an experiment — cumulative from the done-store (shard-count independent)
plus current-run shard activity.

Usage:
    python scripts/exp_status.py                       # defaults to E1_skills_all
    python scripts/exp_status.py experiments/E5_all_domains
"""
import glob
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)
from experiments.common import store  # noqa: E402


def count_rows(path):
    with open(path) as f:
        return sum(1 for _ in f) - 1


def main():
    exp_dir = sys.argv[1] if len(sys.argv) > 1 else "experiments/E1_skills_all"
    exp_dir = os.path.join(REPO, exp_dir) if not os.path.isabs(exp_dir) else exp_dir
    cfg = json.load(open(os.path.join(exp_dir, "config.json")))
    exp, conds = cfg["experiment"], cfg["conditions"]

    if cfg.get("queries_paths"):
        total = sum(count_rows(os.path.join(REPO, p)) for p in cfg["queries_paths"])
    else:
        total = count_rows(os.path.join(REPO, cfg["queries_path"]))

    running = subprocess.run(["pgrep", "-f", "_run_one.py"], capture_output=True).stdout.strip() != b""
    print(f"{exp}  ({'RUNNING' if running else 'idle'})  engine={cfg.get('agent_engine')}  "
          f"workers={cfg.get('max_workers')}")

    # cumulative progress from the store (survives reshards / restarts)
    print("  store (cumulative, resumable):")
    for c in conds:
        done = len(store.done_queries(exp_dir, cfg, c))
        pct = 100.0 * done / total if total else 0
        print(f"    {c:<10}{done:>6}/{total:<6}{pct:>5.0f}%")

    # current-run shard activity (chunks completed this run)
    shard_dirs = sorted(glob.glob(os.path.join(exp_dir, "results", "parallel", "shard_*")))
    if shard_dirs:
        print("  current run — chunks done per shard/condition:")
        for ddir in shard_dirs:
            ckpt = os.path.join(ddir, "results", "checkpoints")
            counts = []
            for c in conds:
                n = len(glob.glob(os.path.join(ckpt, f"{exp}_{c}_chunk*.pkl")))
                counts.append(f"{c}:{n}")
            print(f"    {os.path.basename(ddir):<10}{'  '.join(counts)}")


if __name__ == "__main__":
    main()
