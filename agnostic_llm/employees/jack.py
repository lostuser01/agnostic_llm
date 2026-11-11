"""Jack: software engineering and GitHub Copilot coding specialist."""
from __future__ import annotations
import subprocess
from typing import Optional

from .base import Employee
from ..macos import MacOSStore
from ..types import ToolSpec


def create_jack(store: Optional[MacOSStore] = None) -> Employee:
    store = store or MacOSStore()

    def inspect_repository() -> str:
        """Return the current Git branch and concise working-tree status."""
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            ).stdout.strip()
            return f"Branch: {branch or '(detached)'}\nChanges:\n{status or 'Working tree clean.'}"
        except (OSError, subprocess.SubprocessError) as exc:
            return f"Repository inspection failed: {exc}"

    def run_project_tests() -> str:
        """Run the repository's pytest suite and return its output."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = (result.stdout + result.stderr).strip()
            return f"Exit code: {result.returncode}\n{output[-6000:]}"
        except (OSError, subprocess.SubprocessError) as exc:
            return f"Test execution failed: {exc}"

    tools = [
        ToolSpec(
            "inspect_repository",
            "Inspect the current Git branch and working-tree status before making coding changes.",
            {"type": "object", "properties": {}},
            fn=inspect_repository,
        ),
        ToolSpec(
            "run_project_tests",
            "Run the project's pytest suite after a coding change.",
            {"type": "object", "properties": {}},
            fn=run_project_tests,
        ),
    ]

    prompt = """You are Jack, the Software Engineering Lead and GitHub Copilot specialist.
Work primarily as a coding agent: inspect the repository, understand existing patterns,
make focused production-quality changes, run relevant tests, and explain what changed.
Prefer small, reversible edits and preserve existing behavior. Never claim a change or
test succeeded unless the repository confirms it. Use GitHub Copilot's native coding
capabilities for implementation, debugging, code review, and test generation.
"""

    return Employee(
        name="Jack",
        title="Software Engineering Lead",
        role="Coding, debugging, code review, repository maintenance, and test automation",
        route="copilot",
        voice="Alex",
        avatar="💻",
        system_prompt=prompt,
        tools=tools,
        store=store,
    )
