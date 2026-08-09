"""Re-score ONE condition from its done-store in a fresh process (no cross-condition
state contamination). Prints: condition,n,accuracy,side_effect_rate.

Usage: python experiments/E12_abalation/rescore_isolated.py <condition>
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

import json
import pandas as pd
from experiments.common.scoring import score
from experiments.common import store

HERE = os.path.dirname(__file__)
PM = "data/processed/queries_and_answers/project_management_queries_and_answers.csv"


def main():
    cond = sys.argv[1]
    config = json.load(open(os.path.join(HERE, "config.json")))
    df = store.load_done(HERE, config, cond)
    gt = pd.read_csv(os.path.join(REPO, PM))
    scored = score(df, gt)
    n = len(scored)
    acc = 100.0 * scored["correct"].mean()
    se = 100.0 * scored["unwanted_side_effects"].mean()
    print(json.dumps({"condition": cond, "n": int(n),
                      "accuracy": round(float(acc), 1),
                      "side_effect_rate": round(float(se), 1)}))


if __name__ == "__main__":
    main()
