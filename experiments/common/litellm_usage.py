"""Token capture for the smolagents path (which goes through LiteLLM, not langchain).

Registers ONE persistent litellm callback that accumulates into a process-global counter,
then each `litellm_token_callback()` context measures the DELTA within its block. This is
robust to litellm's callback handling (it doesn't cleanly remove callbacks, so add/remove
per chunk caused later chunks/conditions to capture 0 — the bug that made `skills` show 0
tokens). Mirrors LangChain's get_openai_callback interface.
"""
import contextlib

_ACC = {"prompt": 0, "completion": 0}
_REGISTERED = False


class _Tracker:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def total_cost(self):
        return None  # computed from tokens via experiments.common.pricing


def _ensure_registered():
    """Register a single litellm success callback (once per process)."""
    global _REGISTERED
    if _REGISTERED:
        return True
    try:
        import litellm
        from litellm.integrations.custom_logger import CustomLogger
    except Exception:
        return False

    class _Handler(CustomLogger):
        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            try:
                usage = response_obj.get("usage") if isinstance(response_obj, dict) \
                    else getattr(response_obj, "usage", None)
                if usage is None:
                    return
                get = (lambda k: usage.get(k, 0)) if isinstance(usage, dict) \
                    else (lambda k: getattr(usage, k, 0))
                _ACC["prompt"] += get("prompt_tokens") or 0
                _ACC["completion"] += get("completion_tokens") or 0
            except Exception:
                pass

    litellm.callbacks = list(getattr(litellm, "callbacks", []) or []) + [_Handler()]
    _REGISTERED = True
    return True


@contextlib.contextmanager
def litellm_token_callback():
    """Accumulate LiteLLM token usage within the `with` block (delta of a global counter)."""
    tracker = _Tracker()
    if not _ensure_registered():
        yield tracker
        return
    start_p, start_c = _ACC["prompt"], _ACC["completion"]
    try:
        yield tracker
    finally:
        tracker.prompt_tokens = _ACC["prompt"] - start_p
        tracker.completion_tokens = _ACC["completion"] - start_c
