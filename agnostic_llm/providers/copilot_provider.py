"""GitHub Copilot SDK provider.

The provider keeps the public LLM interface synchronous while running the
official asynchronous Copilot SDK in a short-lived session per request.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from ..base import LLM
from ..types import LLMResponse, Message, ToolSpec, map_exception


def to_copilot_prompt(messages: list[Message]) -> tuple[str, str | None]:
    """Convert provider-neutral messages into a Copilot prompt and system text."""
    system_parts = [m.content for m in messages if m.role == "system" and m.content]
    transcript = []
    for message in messages:
        if message.role == "system":
            continue
        label = {
            "user": "User",
            "assistant": "Assistant",
            "tool": "Tool result",
        }.get(message.role, message.role.title())
        if message.content:
            transcript.append(f"{label}: {message.content}")
        if message.tool_calls:
            names = ", ".join(call.name for call in message.tool_calls)
            transcript.append(f"Assistant requested tools: {names}")
    return "\n\n".join(transcript), "\n\n".join(system_parts) or None


def _run_async(coro):
    """Run a coroutine from both synchronous and async web request contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: list[Any] = []
    error: list[BaseException] = []

    def runner():
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result[0]


class CopilotLLM(LLM):
    """Use GitHub Copilot through the official Copilot Python SDK."""

    def __init__(
        self,
        model: str = "gpt-5",
        api_key: str | None = None,
        github_token: str | None = None,
        working_directory: str | None = None,
        **_: Any,
    ):
        self.model = model
        self.github_token = github_token or api_key
        self.working_directory = working_directory
        self.name = f"copilot:{model}"

    async def _chat_async(self, messages: list[Message], tools: list[ToolSpec] | None):
        try:
            from copilot import CopilotClient, Tool, ToolResult
            from copilot.session import PermissionHandler
            from copilot.session_events import AssistantMessageData
        except ImportError as exc:
            raise RuntimeError(
                "GitHub Copilot support requires the optional 'copilot' dependency. "
                "Install with: python -m pip install -e '.[copilot]'"
            ) from exc

        prompt, system = to_copilot_prompt(messages)
        sdk_tools = []
        for spec in tools or []:
            async def handler(invocation, spec=spec):
                try:
                    value = spec.fn(**(invocation.arguments or {})) if spec.fn else ""
                    if asyncio.iscoroutine(value):
                        value = await value
                    return ToolResult(text_result_for_llm=str(value))
                except Exception as exc:
                    return ToolResult(result_type="failure", error=str(exc))

            sdk_tools.append(Tool(
                name=spec.name,
                description=spec.description,
                parameters=spec.parameters,
                handler=handler,
                skip_permission=True,
            ))

        client_kwargs = {}
        if self.github_token:
            client_kwargs["github_token"] = self.github_token
        if self.working_directory:
            client_kwargs["working_directory"] = self.working_directory

        async with CopilotClient(**client_kwargs) as client:
            session_kwargs = {
                "model": self.model,
                "tools": sdk_tools,
                "on_permission_request": PermissionHandler.approve_all,
            }
            if system:
                session_kwargs["system_message"] = {
                    "mode": "append",
                    "content": system,
                }
            async with await client.create_session(**session_kwargs) as session:
                response = await session.send_and_wait(prompt)
                text = ""
                if response and isinstance(response.data, AssistantMessageData):
                    text = response.data.content
                elif response and hasattr(response.data, "content"):
                    text = response.data.content
                return LLMResponse(text=text, model=self.name, raw=response)

    def chat(self, messages, tools=None, *, temperature=None, max_tokens=None, provider_options=None):
        del temperature, max_tokens
        try:
            return _run_async(self._chat_async(messages, tools))
        except Exception as exc:
            raise map_exception(exc) from exc
