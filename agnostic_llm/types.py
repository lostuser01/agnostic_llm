"""Provider-neutral data types. Your app only ever sees these."""
from __future__ import annotations
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolSpec:
    """Define a tool once; adapters convert it to each provider's format."""
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments
    fn: Callable[..., Any] | None = None


def tool(fn: Callable) -> ToolSpec:
    """Decorator or helper to convert a Python function into a ToolSpec with inferred schema."""
    sig = inspect.signature(fn)
    doc = (inspect.getdoc(fn) or "").strip()
    desc = doc.split("\n\n")[0].replace("\n", " ").strip() if doc else f"Execute {fn.__name__}"
    props = {}
    required = []
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        p_type = type_map.get(param.annotation, "string") if param.annotation != inspect.Parameter.empty else "string"
        props[name] = {"type": p_type}
        if param.default == inspect.Parameter.empty:
            required.append(name)
    schema = {"type": "object", "properties": props, "required": required}
    return ToolSpec(name=fn.__name__, description=desc, parameters=schema, fn=fn)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)  # assistant only
    tool_call_id: str | None = None  # tool only


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: Literal["stop", "tool_calls", "length", "other"] = "stop"
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    raw: Any = None  # untouched provider response, for escape hatches


# ---- Errors: map every provider's exceptions to these so retry logic is uniform
class LLMError(Exception):
    retryable = False


class RateLimitError(LLMError):
    retryable = True


class ProviderUnavailable(LLMError):
    retryable = True


class AuthError(LLMError):
    pass


class BadRequest(LLMError):
    pass


def map_exception(e: Exception) -> LLMError:
    """Best-effort mapping from any SDK exception to our error types."""
    if isinstance(e, LLMError):
        return e
    status = getattr(e, "status_code", None)
    name = type(e).__name__.lower()
    msg = f"{type(e).__name__}: {e}"
    if status == 429 or "ratelimit" in name:
        return RateLimitError(msg)
    if status in (401, 403) or "auth" in name or "permission" in name:
        return AuthError(msg)
    if (isinstance(status, int) and status >= 500) or "connection" in name or "timeout" in name:
        return ProviderUnavailable(msg)
    if status in (400, 404, 413, 422) or "badrequest" in name:
        return BadRequest(msg)
    return LLMError(msg)
