"""Route a MAESTRO model name to the right chat client + provider model id.

Mirrors the ACTOR routing in src/evals/utils.py so the LLM gate (triggers.py) and the
critic (critic.py) hit the same provider as the agent:
  - gpt-*            -> OpenAI API           (openai_key.txt)
  - llama* / qwen*   -> OpenRouter API       (openrouter_key.txt)

Usage:
    client, model_id = chat_client_and_model(model)
    r = client.chat.completions.create(model=model_id, messages=..., **chat_kwargs(model))
"""
import os
from functools import lru_cache

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# MAESTRO model name -> OpenRouter provider model id (same map as src/evals/utils.py).
OPENROUTER_MODELS = {
    "llama3.3-70b": "meta-llama/llama-3.3-70b-instruct",
    "llama3.1-8b": "meta-llama/llama-3.1-8b-instruct",
    "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
    "qwen-2.5-7b": "qwen/qwen-2.5-7b-instruct",
}


@lru_cache(maxsize=None)
def _client(provider: str):
    from openai import OpenAI
    if provider == "openrouter":
        key = open(os.path.join(_REPO, "openrouter_key.txt")).read().strip()
        return OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    key = open(os.path.join(_REPO, "openai_key.txt")).read().strip()
    return OpenAI(api_key=key)


def is_openrouter(model: str) -> bool:
    return model in OPENROUTER_MODELS


def chat_client_and_model(model: str):
    """Return (client, provider_model_id) for a chat.completions call on `model`."""
    if model in OPENROUTER_MODELS:
        return _client("openrouter"), OPENROUTER_MODELS[model]
    return _client("openai"), model


def chat_kwargs(model: str) -> dict:
    """Extra chat.completions kwargs per provider. For OpenRouter models, route to the
    cheapest RELIABLE backend (provider.sort=price, minus providers that 400/429 on the
    72B models); OpenAI models get nothing extra."""
    if model in OPENROUTER_MODELS:
        return {"extra_body": {"provider": {"sort": "price", "ignore": ["Novita"]}}}
    return {}
