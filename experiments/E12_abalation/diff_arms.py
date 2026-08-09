"""Per-query correctness diff between two arms (local, no API).
Usage: python experiments/E12_abalation/diff_arms.py base with_tool_dependency_skills
"""
import os, sys, json
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
import pandas as pd
from experiments.common.scoring import score
from experiments.common import store

HERE = os.path.dirname(__file__)
PM = "data/processed/queries_and_answers/project_management_queries_and_answers.csv"


def scored(cond, config, gt):
    df = score(store.load_done(HERE, config, cond), gt)
    return df.set_index("query")["correct"]


def main():
    a, b = sys.argv[1], sys.argv[2]
    config = json.load(open(os.path.join(HERE, "config.json")))
    gt = pd.read_csv(os.path.join(REPO, PM))
    ca, cb = scored(a, config, gt), scored(b, config, gt)
    idx = ca.index.intersection(cb.index)
    ca, cb = ca[idx], cb[idx]
    gained = [q for q in idx if (not ca[q]) and cb[q]]   # a wrong -> b right
    lost = [q for q in idx if ca[q] and (not cb[q])]     # a right -> b wrong
    print(f"{a}: {int(ca.sum())}/{len(idx)}   {b}: {int(cb.sum())}/{len(idx)}")
    print(f"gained ({b} fixed): {len(gained)} | lost ({b} broke): {len(lost)}")
    print("\n-- LOST (right in base, wrong with tool-dep) --")
    for q in lost:
        print(" •", q[:110])
    print("\n-- GAINED --")
    for q in gained:
        print(" •", q[:110])


if __name__ == "__main__":
    main()
