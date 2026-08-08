"""List org projects and their per-model rate limits via the Admin API.

Reads openai_admin_key.txt (ADMIN key). Tells you whether you and a teammate share one
project (hence one TPM ceiling) or have separate limits.

Usage:
    python scripts/check_project_limits.py
    python scripts/check_project_limits.py --model gpt-4o-mini-2024-07-18
"""
import argparse
import os

import requests

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE = "https://api.openai.com/v1/organization"


def read_key(path="openai_admin_key.txt"):
    with open(os.path.join(REPO, path)) as f:
        return f.read().strip()


def get(url, key, params=None):
    r = requests.get(url, headers={"Authorization": f"Bearer {key}"}, params=params or {}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="filter to one model")
    args = ap.parse_args()
    key = read_key()

    try:
        projects = get(f"{BASE}/projects", key, {"limit": 100}).get("data", [])
    except RuntimeError as e:
        print(e)
        print("\nNeeds an ADMIN key with org read scope (api.management.read).")
        return

    print(f"Projects: {len(projects)}\n")
    for proj in projects:
        pid, name, status = proj.get("id"), proj.get("name"), proj.get("status")
        print(f"● {name}  ({pid})  [{status}]")
        try:
            limits = get(f"{BASE}/projects/{pid}/rate_limits", key, {"limit": 100}).get("data", [])
        except RuntimeError as e:
            print(f"    (rate limits unavailable: {e})")
            continue
        rows = [x for x in limits if (not args.model or x.get("model") == args.model)]
        if not rows:
            print("    (no rate limits listed)")
        for x in rows:
            print(f"    {x.get('model',''):<28} "
                  f"TPM={x.get('max_tokens_per_1_minute','?'):>10}  "
                  f"RPM={x.get('max_requests_per_1_minute','?'):>8}")
        print()

    print("If you and your teammate use the SAME project id, you share one TPM ceiling.")
    print("Separate projects → separate limits (an org owner can set per-project caps).")


if __name__ == "__main__":
    main()
