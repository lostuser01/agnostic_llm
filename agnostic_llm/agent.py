from __future__ import annotations
from .base import LLM
from .types import Message, ToolSpec
from .security import ApprovalRequired


def run_agent(llm: LLM, prompt: str, tools: list[ToolSpec], system: str | None = None,
              max_steps: int = 8, approval_checker=None, **opts):
    """Provider-independent tool loop. Returns (final_text, full_message_history)."""
    by_name = {t.name: t for t in tools}
    msgs = [Message("system", system)] if system else []
    msgs.append(Message("user", prompt))
    for _ in range(max_steps):
        r = llm.chat(msgs, tools=tools, **opts)
        msgs.append(Message("assistant", r.text, r.tool_calls))
        if not r.tool_calls:
            return r.text, msgs
        for tc in r.tool_calls:
            spec = by_name.get(tc.name)
            if spec is None or spec.fn is None:
                out = f"Error: Unknown or unavailable tool '{tc.name}'"
                msgs.append(Message("tool", out, tool_call_id=tc.id))
                continue
            try:
                if approval_checker:
                    approval_checker(spec, tc)
                out = str(spec.fn(**tc.arguments))
            except ApprovalRequired:
                raise
            except Exception as e:  # let the model see and recover from tool errors
                out = f"Error: {e}"
            msgs.append(Message("tool", out, tool_call_id=tc.id))
    raise RuntimeError(f"agent did not finish in {max_steps} steps")
