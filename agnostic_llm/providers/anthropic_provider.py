from __future__ import annotations
from ..base import LLM
from ..types import LLMResponse, Message, ToolCall, ToolSpec, Usage, map_exception

_STOP = {"end_turn": "stop", "stop_sequence": "stop", "tool_use": "tool_calls", "max_tokens": "length"}


def to_anthropic(messages: list[Message], tools: list[ToolSpec] | None):
    system, out = [], []
    for m in messages:
        if m.role == "system":
            system.append(m.content)
        elif m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            blocks = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
            out.append({"role": "assistant", "content": blocks or m.content})
        elif m.role == "tool":
            block = {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
            prev = out[-1] if out else None
            # Anthropic wants all results for one turn in a single user message
            if (prev and prev["role"] == "user" and isinstance(prev["content"], list)
                    and prev["content"] and prev["content"][0].get("type") == "tool_result"):
                prev["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
    t = [{"name": x.name, "description": x.description, "input_schema": x.parameters}
         for x in (tools or [])]
    return "\n\n".join(system), out, t


class AnthropicLLM(LLM):
    def __init__(self, model: str, api_key: str | None = None, **client_kwargs):
        import anthropic  # lazy: only needed if you use this provider
        self.client = anthropic.Anthropic(api_key=api_key, **client_kwargs)
        self.model = model
        self.name = f"anthropic:{model}"

    def chat(self, messages, tools=None, *, temperature=None, max_tokens=None, provider_options=None):
        system, msgs, t = to_anthropic(messages, tools)
        req = {"model": self.model, "messages": msgs, "max_tokens": max_tokens or 2048}
        if system:
            req["system"] = system
        if t:
            req["tools"] = t
        if temperature is not None:
            req["temperature"] = temperature
        req.update(provider_options or {})
        try:
            r = self.client.messages.create(**req)
        except Exception as e:
            raise map_exception(e) from e
        text = "".join(b.text for b in r.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in r.content if b.type == "tool_use"]
        return LLMResponse(text, calls, _STOP.get(r.stop_reason, "other"),
                           Usage(r.usage.input_tokens, r.usage.output_tokens), r.model, r)
