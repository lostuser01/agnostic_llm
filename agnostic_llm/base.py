from __future__ import annotations
from abc import ABC, abstractmethod
from .types import LLMResponse, Message, ToolSpec


class LLM(ABC):
    """The only interface your application depends on."""
    name: str = "llm"

    @abstractmethod
    def chat(self, messages: list[Message], tools: list[ToolSpec] | None = None,
             *, temperature: float | None = None, max_tokens: int | None = None,
             provider_options: dict | None = None) -> LLMResponse:
        """provider_options is merged into the raw request, so you can still use
        provider-specific features (caching, thinking, etc.) without leaking them
        into the rest of your code."""

    def ask(self, prompt: str, system: str | None = None, **opts) -> str:
        msgs = [Message("system", system)] if system else []
        msgs.append(Message("user", prompt))
        return self.chat(msgs, **opts).text
