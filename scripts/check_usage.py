"""Token usage by model via the Admin Usage API. Reads openai_admin_key.txt (ADMIN key).

More detailed than costs: input/output tokens + request counts per model. Optionally group
by project or api key to see your share vs. a teammate's.

Usage:
    python scripts/check_usage.py                 # last 7 days, by model
    python scripts/check_usage.py --days 30
    python scripts/check_usage.py --group project # split by project
"""
import argparse
import os
import sys
import time
from collections import defaultdict

import requests

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)
from experiments.common.pricing import cost_usd  # noqa: E402


def read_key(path="openai_admin_key.txt"):
    with open(os.path.join(REPO, path)) as f:
        return f.read().strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--group", choices=["model", "project", "api_key", "user"], default="model")
    args = ap.parse_args()

    group_field = {"project": "project_id", "api_key": "api_key_id",
                   "user": "user_id", "model": "model"}[args.group]

    key = read_key()
    start = int(time.time()) - args.days * 86400
    url = "https://api.openai.com/v1/organization/usage/completions"
    # API caps limit at 31 daily buckets
    params = {"start_time": start, "bucket_width": "1d", "limit": min(31, args.days + 1),
              "group_by": ["model", group_field] if group_field != "model" else ["model"]}

    agg = defaultdict(lambda: {"in": 0, "out": 0, "req": 0})
    page = None
    while True:
        p = dict(params)
        if page:
            p["page"] = page
        r = requests.get(url, headers={"Authorization": f"Bearer {key}"}, params=p, timeout=30)
        if r.status_code != 200:
            print(f"HTTP {r.status_code}: {r.text[:300]}")
            if r.status_code in (401, 403):
                print("\nNeeds an ADMIN key with api.usage.read scope.")
            return
        data = r.json()
        for bucket in data.get("data", []):
            for res in bucket.get("results", []):
                model = res.get("model", "?")
                grp = res.get(group_field, "") if group_field != "model" else ""
                k = f"{model}  [{grp}]" if grp else model
                agg[k]["in"] += res.get("input_tokens", 0) or 0
                agg[k]["out"] += res.get("output_tokens", 0) or 0
                agg[k]["req"] += res.get("num_model_requests", 0) or 0
        if data.get("has_more") and data.get("next_page"):
            page = data["next_page"]
        else:
            break

    print(f"Usage — last {args.days} days, by {args.group}")
    print(f"{'model / group':<40}{'in tok':>14}{'out tok':>14}{'requests':>10}{'~cost $':>10}")
    print("-" * 88)
    ti = to = tr = tc = 0.0
    for k, v in sorted(agg.items(), key=lambda x: -(x[1]["in"] + x[1]["out"])):
        model = k.split("  [")[0]
        c = cost_usd(model, v["in"], v["out"])
        cs = "-" if c is None else f"{c:.4f}"
        print(f"{k:<40}{v['in']:>14,}{v['out']:>14,}{v['req']:>10,}{cs:>10}")
        ti += v["in"]; to += v["out"]; tr += v["req"]; tc += (c or 0)
    print("-" * 88)
    print(f"{'TOTAL':<40}{ti:>14,.0f}{to:>14,.0f}{tr:>10,.0f}{tc:>10.4f}")
    print("\nNote: cost is estimated from experiments/common/pricing.py for known models only.")


if __name__ == "__main__":
    main()
