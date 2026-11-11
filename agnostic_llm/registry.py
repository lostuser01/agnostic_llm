"""Model choice lives in config, not code."""
from __future__ import annotations
import os
from typing import Callable
from .base import LLM
from .router import FallbackLLM
from .types import LLMError
from .yaml_helper import load_config_data


class UnavailableLLM(LLM):
    """Placeholder when a provider's library is not installed or cannot be initialized."""
    def __init__(self, key: str, reason: str):
        self.name = f"unavailable[{key}]"
        self.reason = reason

    def chat(self, messages, tools=None, **opts):
        raise LLMError(f"{self.name}: {self.reason}")


def _anthropic(**kw):
    from .providers.anthropic_provider import AnthropicLLM
    return AnthropicLLM(**kw)


def _openai(**kw):
    from .providers.openai_provider import OpenAILLM
    return OpenAILLM(**kw)


def _mock(**kw):
    from .providers.mock import MockLLM
    return MockLLM(**kw)


def _copilot(**kw):
    from .providers.copilot_provider import CopilotLLM
    return CopilotLLM(**kw)


PROVIDERS: dict[str, Callable[..., LLM]] = {
    "anthropic": _anthropic,
    "openai": _openai,
    "copilot": _copilot,
    "mock": _mock,
}


def register_provider(name: str, factory: Callable[..., LLM]):
    """Add a new backend (Bedrock, Vertex, a custom HTTP API...) without touching the core."""
    PROVIDERS[name] = factory


class Models:
    def __init__(self, config: dict):
        self.cfg, self._cache = config, {}

    @classmethod
    def from_file(cls, path: str):
        return cls(load_config_data(path))

    def _build(self, key: str) -> LLM:
        spec = dict(self.cfg["models"][key])
        provider = spec.pop("provider")
        env = spec.pop("api_key_env", None)
        if env:
            spec["api_key"] = os.environ.get(env)
        try:
            return PROVIDERS[provider](**spec)
        except Exception as e:
            return UnavailableLLM(key, str(e))

    def get(self, name: str = "default") -> LLM:
        """`name` is either a route (ordered fallback list) or a single model key."""
        if name in self._cache:
            return self._cache[name]
        routes = self.cfg.get("routes", {})
        if name in routes:
            llm = FallbackLLM([self._build(k) for k in routes[name]])
        elif name in self.cfg["models"]:
            llm = self._build(name)
        else:
            raise KeyError(f"unknown model or route: {name}")
        self._cache[name] = llm
        return llm
