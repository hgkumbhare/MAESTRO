"""Token pricing → USD cost. Update prices from https://platform.openai.com/pricing.

Prices are USD per 1,000,000 tokens (input, output).
"""

PRICES = {
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4o": (2.50, 10.00),
    # OpenRouter models (E1.9 cross-model). Update from https://openrouter.ai/models.
    "llama3.3-70b": (0.12, 0.30),
    "qwen-2.5-72b": (0.12, 0.39),
    "llama3.1-8b": (0.02, 0.03),
    "qwen-2.5-7b": (0.04, 0.10),
    # embeddings (the embedding gate uses text-embedding-3-small); output tokens = 0.
    "text-embedding-3-small": (0.02, 0.0),
}


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int):
    """Return computed USD cost, or None if the model's price is unknown."""
    price = PRICES.get(model)
    if not price:
        return None
    pin, pout = price
    return round(prompt_tokens / 1e6 * pin + completion_tokens / 1e6 * pout, 6)


def cost_report(model: str, prompt_tokens: int, completion_tokens: int,
                n_queries: int, n_correct: float):
    """Efficiency view: total $, $/query, and $ per CORRECT answer (the honest metric —
    a method that costs more but gets more right can still be cheaper per solved task)."""
    total = cost_usd(model, prompt_tokens, completion_tokens)
    if total is None:
        return {"cost_usd": None, "usd_per_query": None, "usd_per_correct": None}
    return {
        "cost_usd": total,
        "usd_per_query": round(total / n_queries, 5) if n_queries else None,
        "usd_per_correct": round(total / n_correct, 5) if n_correct else None,
    }
