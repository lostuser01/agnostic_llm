"""Base Employee class for the autonomous agent roster.
Each employee is an autonomous persona with a specialized role, assigned model/route,
system prompt, personal toolset, persistent memory, and ability to delegate.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TYPE_CHECKING
from ..base import LLM
from ..types import Message, ToolSpec, ToolCall
from ..agent import run_agent
from ..macos import MacOSStore

if TYPE_CHECKING:
    from .roster import EmployeeRoster

log = logging.getLogger("agnostic_llm.employee")


@dataclass
class EmployeeExecutionResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    employee_name: str = ""
    delegated_to: Optional[str] = None
    messages: list[Message] = field(default_factory=list)


class Employee:
    """An autonomous AI employee with a defined persona, tools, and model route."""

    def __init__(
        self,
        name: str,
        title: str,
        role: str,
        route: str = "default",
        voice: str = "Samantha",
        avatar: str = "🤖",
        system_prompt: str = "",
        tools: Optional[list[ToolSpec]] = None,
        llm: Optional[LLM] = None,
        store: Optional[MacOSStore] = None,
        roster: Optional[EmployeeRoster] = None,
    ):
        self.name = name
        self.title = title
        self.role = role
        self.route = route
        self.voice = voice
        self.avatar = avatar
        self.system_prompt = system_prompt
        self.tools: list[ToolSpec] = list(tools or [])
        self.llm = llm
        self.store = store or MacOSStore()
        self.roster = roster
        self._history: list[Message] = []

        # Wire delegation tool
        self._register_delegation_tool()

    def set_llm(self, llm: LLM):
        self.llm = llm

    def set_roster(self, roster: EmployeeRoster):
        self.roster = roster

    def _register_delegation_tool(self):
        """Allow this employee to delegate tasks or request help from peers."""
        def delegate_task(target_employee: str, instruction: str) -> str:
            """Delegate a specialized sub-task to another employee on the team.
            Available employees: Alex (Day Planner & Schedule), Morgan (Freelance & BizDev),
            Taylor (Marketing & Growth), Elena (High-Empathy Writing & Manuscripts).
            """
            if not self.roster:
                return f"Error: No roster connected to delegate to {target_employee}"
            emp = self.roster.get(target_employee)
            if not emp:
                return f"Error: Employee '{target_employee}' not found in team roster."
            log.info("[%s] Delegating task to [%s]: %s", self.name, emp.name, instruction)
            res = emp.chat(instruction, conversation_history=[])
            return f"[{emp.name}'s Output]:\n{res.text}"

        spec = ToolSpec(
            name="delegate_task",
            description="Delegate a specialized sub-task to another employee on the team (Alex, Morgan, Taylor, Elena).",
            parameters={
                "type": "object",
                "properties": {
                    "target_employee": {"type": "string", "description": "Name of the employee (e.g. Alex, Morgan, Taylor, Elena)"},
                    "instruction": {"type": "string", "description": "Clear, detailed instruction for what the employee should produce"},
                },
                "required": ["target_employee", "instruction"],
            },
            fn=delegate_task,
        )
        # Avoid duplicate tool
        if not any(t.name == "delegate_task" for t in self.tools):
            self.tools.append(spec)

    def add_tool(self, tool: ToolSpec):
        if not any(t.name == tool.name for t in self.tools):
            self.tools.append(tool)

    def remember(self, key: str, value: str):
        self.store.remember(self.name, key, value)

    def recall(self, key: Optional[str] = None) -> list[dict]:
        return self.store.recall(self.name, key)

    def chat(
        self,
        prompt: str,
        conversation_history: Optional[list[Message]] = None,
        max_steps: int = 8,
        **opts
    ) -> EmployeeExecutionResult:
        """Run the employee agent loop against user input with its tools and persona."""
        if self.llm is None:
            raise RuntimeError(f"Employee '{self.name}' has no LLM assigned. Call set_llm() first.")

        # Build context from recent memories
        memories = self.recall()
        mem_str = ""
        if memories:
            items = [f"- {m['key']}: {m['value']}" for m in memories[:5]]
            mem_str = "\n\nKnown Domain Memory / Context:\n" + "\n".join(items)

        full_system = f"{self.system_prompt}{mem_str}\n\nYou are {self.name}, {self.title}. Address the user with executive competence and clear, actionable value."

        # Maintain or build messages
        history = list(conversation_history or self._history)
        if not history:
            history.append(Message("system", full_system))

        # Check if system message needs updating
        if history and history[0].role == "system":
            history[0] = Message("system", full_system)

        final_text, updated_history = run_agent(
            llm=self.llm,
            prompt=prompt,
            tools=self.tools,
            system=full_system,
            max_steps=max_steps,
            **opts
        )

        # Store in internal history
        self._history = updated_history

        # Collect executed tool calls
        all_calls = []
        for msg in updated_history:
            if msg.role == "assistant" and msg.tool_calls:
                all_calls.extend(msg.tool_calls)

        return EmployeeExecutionResult(
            text=final_text,
            tool_calls=all_calls,
            employee_name=self.name,
            messages=updated_history,
        )

