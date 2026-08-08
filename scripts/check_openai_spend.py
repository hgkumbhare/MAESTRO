"""Query OpenAI spend via the Admin Costs API.

Reads an ADMIN key from openai_admin_key.txt (repo root) — NOT the inference key.
Create an admin key at https://platform.openai.com/settings/organization/admin-keys

Usage:
    python scripts/check_openai_spend.py            # last 30 days
    python scripts/check_openai_spend.py --days 7
"""
import argparse
import time

import requests


def read_key(path="openai_admin_key.txt"):
    with open(path) as f:
        return f.read().strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    key = read_key()
    start = int(time.time()) - args.days * 86400

    url = "https://api.openai.com/v1/organization/costs"
    headers = {"Authorization": f"Bearer {key}"}
    params = {"start_time": start, "bucket_width": "1d", "limit": 180}

    total = 0.0
    currency = "usd"
    page = 0
    while True:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            print(f"HTTP {r.status_code}: {r.text[:300]}")
            if r.status_code in (401, 403):
                print("\nThis endpoint needs an ADMIN key with api.usage.read scope "
                      "(not your inference key).")
            return
        data = r.json()
        for bucket in data.get("data", []):
            for res in bucket.get("results", []):
                amt = res.get("amount", {})
                total += float(amt.get("value", 0) or 0)
                currency = amt.get("currency", currency)
        page += 1
        if data.get("has_more") and data.get("next_page"):
            params["page"] = data["next_page"]
        else:
            break

    print(f"Total spend, last {args.days} days: {total:.4f} {currency.upper()} "
          f"(across {page} page(s))")
    print("Note: this is *spend*, not remaining balance. Balance is dashboard-only:")
    print("  https://platform.openai.com/settings/organization/billing/overview")


if __name__ == "__main__":
    main()
