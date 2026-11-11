from __future__ import annotations
from ..base import LLM
from ..types import LLMResponse


class MockLLM(LLM):
    """Scripted model for tests/demos. Items may be LLMResponse, str, or an Exception to raise."""

    def __init__(self, script=None, name="mock", **_):
        self.script, self.name, self.calls = list(script or ["(mock reply)"]), name, []

    def chat(self, messages, tools=None, **opts):
        self.calls.append(messages)
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, LLMResponse) else LLMResponse(text=item, model=self.name)
