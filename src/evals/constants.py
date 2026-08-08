"""Central experiment constants.

Single source of truth for the knobs that affect results, so they can't drift between
the langchain and smolagents code paths (they previously did: langchain used temp 0,
smolagents used 0.7 — a reproducibility bug).

TEMPERATURE = 0 is the right default for WorkBench: each task has a unique correct
outcome, so greedy decoding maximizes accuracy AND makes runs reproducible (low variance,
fewer seeds needed). Applies to BOTH engines.
"""

# Sampling temperature for the agent LLM (both langchain and smolagents).
TEMPERATURE = 0

# Seed for best-effort reproducibility (agent + LLM gate). OpenAI's seed is best-effort
# (paired with system_fingerprint), not a guarantee, but sharply reduces run-to-run drift.
SEED = 42

# Temperature used only for the "no actions taken" retry path (langchain).
RETRY_TEMPERATURE = 0.5

# ReAct agent limits (langchain).
MAX_ITERATIONS = 20
MAX_EXECUTION_TIME = 120  # seconds

# smolagents rate-limit retry (patched into smolagents.models at import in utils.py).
# smolagents defaults to a 60s base wait × 3 attempts → up to ~3 min per throttled query,
# ignoring OpenAI's Retry-After header. A 10s base recovers just as well on Tier 2 with
# far shorter stalls: waits ~10s then ~20s (≤ ~30s) instead of ~60s then ~120s.
SMOLAGENTS_RETRY_WAIT = 10          # base backoff seconds (smolagents default 60)
SMOLAGENTS_RETRY_MAX_ATTEMPTS = 3   # retry attempts on rate-limit errors
