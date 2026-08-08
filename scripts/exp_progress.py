"""Quick per-shard query counts for a running experiment (parallel or sequential).

Lightweight view; use exp_monitor.py for health/stalls and exp_status.py for the store.

Usage:
    python scripts/exp_progress.py                      # defaults to E1_skills_all
    python scripts/exp_progress.py experiments/E5_all_domains
"""
import glob
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def count_queries(log):
    if not os.path.exists(log):
        return 0
    with open(log, errors="ignore") as f:
        return f.read().count("### Query:")


def main():
    exp_dir = sys.argv[1] if len(sys.argv) > 1 else "experiments/E1_skills_all"
    exp_dir = os.path.join(REPO, exp_dir) if not os.path.isabs(exp_dir) else exp_dir

    running = subprocess.run(["pgrep", "-f", "_run_one.py|run.py"],
                             capture_output=True).stdout.strip() != b""
    status = "RUNNING" if running else "not running (finished or not started)"

    shard_dirs = sorted(glob.glob(os.path.join(exp_dir, "results", "parallel", "*")))
    if shard_dirs:
        print(f"[exp] status: {status} | mode: parallel")
        for d in shard_dirs:
            if os.path.isdir(d):
                print(f"  {os.path.basename(d):<12}{count_queries(os.path.join(d, 'run.log')):>5} queries")
    else:
        n = count_queries(os.path.join(exp_dir, "results", "run.log"))
        print(f"[exp] status: {status} | mode: sequential | queries: {n}")


if __name__ == "__main__":
    main()
