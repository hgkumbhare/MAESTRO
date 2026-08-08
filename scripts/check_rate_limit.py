"""Check your OpenAI rate limits (TPM/RPM) by reading response headers.

Uses the inference key in openai_key.txt. A minimal call returns the current limits,
so this also reveals whether a tier upgrade has propagated (TPM jumps 200k -> 2M at Tier 2).

Usage:
    python scripts/check_rate_limit.py
    python scripts/check_rate_limit.py --model gpt-4o-2024-08-06
"""
import argparse

import requests


def read_key(path="openai_key.txt"):
    with open(path) as f:
        return f.read().strip()


TIERS = {200_000: "Tier 1", 2_000_000: "Tier 2", 4_000_000: "Tier 3",
         10_000_000: "Tier 4", 150_000_000: "Tier 5"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o-mini-2024-07-18")
    args = ap.parse_args()

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {read_key()}", "Content-Type": "application/json"},
        json={"model": args.model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
        timeout=30,
    )
    h = r.headers
    tpm = int(h.get("x-ratelimit-limit-tokens", 0))
    tier = TIERS.get(tpm, "unknown")

    print(f"model: {args.model}")
    print(f"  tokens/min (TPM):   {tpm:>12,}   ({tier})")
    print(f"  requests/min (RPM): {int(h.get('x-ratelimit-limit-requests', 0)):>12,}")
    print(f"  remaining tokens:   {int(h.get('x-ratelimit-remaining-tokens', 0)):>12,}")
    print(f"  remaining requests: {int(h.get('x-ratelimit-remaining-requests', 0)):>12,}")
    print(f"  token reset in:     {h.get('x-ratelimit-reset-tokens', '?'):>12}")
    if tpm and tpm < 2_000_000:
        print("\n  → still Tier 1. Tier 2 (2M TPM) needs $50 total paid + 7 days since first payment.")
    elif tpm >= 2_000_000:
        print("\n  → upgrade is LIVE. You can raise max_workers now.")


if __name__ == "__main__":
    main()
