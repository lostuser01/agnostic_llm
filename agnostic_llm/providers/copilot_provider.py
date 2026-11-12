"""GitHub Copilot SDK provider.

The provider keeps the public LLM interface synchronous while running the
official asynchronous Copilot SDK in a short-lived session per request.
"""
from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any

from ..base import LLM
from ..types import LLMResponse, Message, ToolSpec, map_exception
from ..macos import DB_PATH
from ..security import SecurityStore, validate_shell_command


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
        security_db_path: str | None = None,
        approval_timeout_seconds: int = 300,
        **_: Any,
    ):
        self.model = model
        self.github_token = github_token or api_key
        self.working_directory = str(Path(working_directory or Path.cwd()).resolve())
        self.security = SecurityStore(Path(security_db_path or DB_PATH))
        self.security.allow_workspace(self.working_directory)
        self.approval_timeout_seconds = approval_timeout_seconds
        self.name = f"copilot:{model}"

    async def _permission_handler(self, request, invocation):
        from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject

        kind = getattr(request, "kind", "unknown")
        if kind == "read":
            paths = [getattr(request, "path", "")]
        elif kind == "shell":
            paths = list(getattr(request, "possible_paths", []) or [])
        elif kind == "write":
            paths = [getattr(request, "path", "")]
        else:
            paths = []
        paths = [str(path) for path in paths if path]
        if paths and not all(self.security.is_workspace_allowed(path) for path in paths):
            self.security.audit("copilot", "permission.denied", kind, {"paths": paths})
            return PermissionDecisionReject(feedback="Path is outside the configured workspace allowlist.")

        details = {
            "kind": kind,
            "intention": getattr(request, "intention", ""),
            "paths": paths,
            "command": getattr(request, "full_command_text", ""),
            "working_directory": getattr(request, "resolved_working_directory", self.working_directory),
        }
        if kind == "shell":
            command = str(getattr(request, "full_command_text", ""))
            safe, reasons = validate_shell_command(command)
            if not safe:
                self.security.audit("copilot", "permission.blocked", "copilot.shell", {
                    **details, "reasons": reasons,
                })
                return PermissionDecisionReject(
                    feedback="Command blocked by local security policy: " + "; ".join(reasons)
                )
        action = f"copilot.{kind}"
        decision = self.security.get_approval(action)
        if decision == "allow":
            self.security.audit("copilot", "permission.approved", action, details)
            return PermissionDecisionApproveOnce()
        if decision == "deny":
            self.security.audit("copilot", "permission.denied", action, details)
            return PermissionDecisionReject(feedback="Denied by local approval policy.")

        request_id = self.security.create_approval_request("copilot", action, details)
        deadline = time.monotonic() + self.approval_timeout_seconds
        while time.monotonic() < deadline:
            current = next(
                (item for item in self.security.list_pending_approvals() if item["id"] == request_id),
                None,
            )
            if current is None:
                policy = self.security.get_approval(action)
                if policy == "allow":
                    return PermissionDecisionApproveOnce()
                return PermissionDecisionReject(feedback="Approval denied or expired.")
            await asyncio.sleep(0.5)
        self.security.resolve_approval(request_id, "deny", remember=False)
        return PermissionDecisionReject(feedback="Approval request timed out.")

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
                "on_permission_request": self._permission_handler,
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
