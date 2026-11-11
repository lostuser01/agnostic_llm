from __future__ import annotations
import logging, time
from .base import LLM
from .types import LLMError

log = logging.getLogger("agnostic_llm")


class FallbackLLM(LLM):
    """Tries each model in order. Retries transient errors with backoff, then fails over."""

    def __init__(self, models: list[LLM], retries: int = 2, backoff: float = 1.0):
        self.models, self.retries, self.backoff = models, retries, backoff
        self.name = "fallback[" + ",".join(m.name for m in models) + "]"

    def chat(self, messages, tools=None, **opts):
        last: Exception | None = None
        for m in self.models:
            for attempt in range(self.retries + 1):
                try:
                    return m.chat(messages, tools, **opts)
                except LLMError as e:
                    last = e
                    log.warning("%s failed (%s): %s", m.name, type(e).__name__, e)
                    if e.retryable and attempt < self.retries:
                        time.sleep(self.backoff * 2 ** attempt)
                        continue
                    break  # non-retryable or out of retries -> next model
        raise last or LLMError("no models configured")
