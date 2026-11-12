"""Jack: software engineering and GitHub Copilot coding specialist."""
from __future__ import annotations
import subprocess
import os
from pathlib import Path
from typing import Optional

from .base import Employee
from ..macos import MacOSStore
from ..security import SecurityStore
from ..security import validate_shell_command
from ..types import ToolSpec
from ..integrations import GitHubProvider, DisabledGitHubProvider, IntegrationNotConfigured


def create_jack(
    store: Optional[MacOSStore] = None,
    github_provider: GitHubProvider | None = None,
) -> Employee:
    store = store or MacOSStore()
    workspace_root = Path(os.environ.get("AGNOSTIC_REPO_ROOT", Path.cwd())).expanduser().resolve()
    security = SecurityStore(store.db_path)
    security.allow_workspace(str(workspace_root))
    github_provider = github_provider or DisabledGitHubProvider()

    def inspect_repository() -> str:
        """Return the current Git branch and concise working-tree status."""
        if not security.is_workspace_allowed(str(workspace_root)):
            return f"Workspace is not allowlisted: {workspace_root}"
        try:
            branch = subprocess.run(
                ["git", "-C", str(workspace_root), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "-C", str(workspace_root), "status", "--short"],
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
        if not security.is_workspace_allowed(str(workspace_root)):
            return f"Workspace is not allowlisted: {workspace_root}"
        safe, reasons = validate_shell_command("python -m pytest -q")
        if not safe:
            return f"Test command blocked by security policy: {'; '.join(reasons)}"
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-q"],
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = (result.stdout + result.stderr).strip()
            return f"Exit code: {result.returncode}\n{output[-6000:]}"
        except (OSError, subprocess.SubprocessError) as exc:
            return f"Test execution failed: {exc}"

    def inspect_github_repository(owner: str, name: str) -> str:
        """Read repository metadata through the configured GitHub provider."""
        try:
            return str(github_provider.repository(owner, name))
        except IntegrationNotConfigured as exc:
            return str(exc)

    def create_github_pull_request(owner: str, name: str, title: str, head: str, base: str, body: str = "") -> str:
        """Create a pull request through GitHub after approval."""
        try:
            result = github_provider.create_pull_request(owner, name, title, head, base, body)
        except IntegrationNotConfigured as exc:
            return str(exc)
        return f"Pull request created: {result}"

    def run_github_ci(owner: str, name: str, ref: str = "") -> str:
        """Request a CI run through the configured GitHub provider."""
        try:
            result = github_provider.run_ci(owner, name, ref)
        except IntegrationNotConfigured as exc:
            return str(exc)
        return f"CI run requested: {result}"

    def get_github_ci_status(owner: str, name: str, ref: str = "") -> str:
        """Read CI status through the configured GitHub provider."""
        try:
            result = github_provider.ci_status(owner, name, ref)
        except IntegrationNotConfigured as exc:
            return str(exc)
        return f"CI status: {result}"

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
        ToolSpec("inspect_github_repository", "Read GitHub repository metadata.",
                 {"type": "object", "properties": {"owner": {"type": "string"}, "name": {"type": "string"}},
                  "required": ["owner", "name"]}, fn=inspect_github_repository),
        ToolSpec("create_github_pull_request", "Create a GitHub pull request after approval.",
                 {"type": "object", "properties": {
                     "owner": {"type": "string"}, "name": {"type": "string"}, "title": {"type": "string"},
                     "head": {"type": "string"}, "base": {"type": "string"}, "body": {"type": "string"}
                 }, "required": ["owner", "name", "title", "head", "base"]},
                 fn=create_github_pull_request, approval_key="github.pull_request.create",
                 approval_description="Create a GitHub pull request"),
        ToolSpec("run_github_ci", "Request a GitHub Actions CI run after approval.",
                 {"type": "object", "properties": {
                     "owner": {"type": "string"}, "name": {"type": "string"}, "ref": {"type": "string"}
                 }, "required": ["owner", "name"]}, fn=run_github_ci,
                 approval_key="github.ci.run", approval_description="Request a GitHub CI run"),
        ToolSpec("get_github_ci_status", "Read GitHub Actions CI status.",
                 {"type": "object", "properties": {
                     "owner": {"type": "string"}, "name": {"type": "string"}, "ref": {"type": "string"}
                 }, "required": ["owner", "name"]}, fn=get_github_ci_status),
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
