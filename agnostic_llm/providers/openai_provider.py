from __future__ import annotations
import json
from ..base import LLM
from ..types import LLMResponse, Message, ToolCall, ToolSpec, Usage, map_exception

_STOP = {"stop": "stop", "tool_calls": "tool_calls", "length": "length"}


def to_openai(messages: list[Message], tools: list[ToolSpec] | None):
    out = []
    for m in messages:
        if m.role in ("system", "user"):
            out.append({"role": m.role, "content": m.content})
        elif m.role == "assistant":
            d = {"role": "assistant", "content": m.content or None}
            if m.tool_calls:
                d["tool_calls"] = [{"id": c.id, "type": "function",
                                    "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                                   for c in m.tool_calls]
            out.append(d)
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
    t = [{"type": "function", "function": {"name": x.name, "description": x.description,
                                           "parameters": x.parameters}} for x in (tools or [])]
    return out, t


class OpenAILLM(LLM):
    """Works with OpenAI AND anything OpenAI-compatible: Gemini, Ollama, vLLM,
    LM Studio, OpenRouter, Together, Groq, ... just set base_url."""

    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None, **client_kwargs):
        import openai
        self.client = openai.OpenAI(api_key=api_key or ("none" if base_url else None),
                                    base_url=base_url, **client_kwargs)
        self.model, self.base_url = model, base_url
        self.name = f"openai:{model}" if not base_url else f"{base_url}:{model}"

    def chat(self, messages, tools=None, *, temperature=None, max_tokens=None, provider_options=None):
        msgs, t = to_openai(messages, tools)
        req = {"model": self.model, "messages": msgs}
        if t:
            req["tools"] = t
        if temperature is not None:
            req["temperature"] = temperature
        if max_tokens:
            # real OpenAI's newer models reject max_tokens; compatible servers want it
            req["max_completion_tokens" if not self.base_url else "max_tokens"] = max_tokens
        req.update(provider_options or {})
        try:
            r = self.client.chat.completions.create(**req)
        except Exception as e:
            raise map_exception(e) from e
        ch = r.choices[0]
        calls = []
        for c in ch.message.tool_calls or []:
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(c.id, c.function.name, args))
        u = r.usage
        return LLMResponse(ch.message.content or "", calls, _STOP.get(ch.finish_reason, "other"),
                           Usage(getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0)),
                           r.model, r)
