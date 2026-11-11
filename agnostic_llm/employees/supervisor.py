"""Supervisor: Master Team Orchestrator.
Coordinates the entire array of AI employees (Alex, Morgan, Taylor, Elena).
Routes tasks to the most qualified specialist or orchestrates multi-agent collaboration.
"""
from __future__ import annotations
from typing import Optional
from .base import Employee
from ..types import ToolSpec
from ..macos import MacOSStore, send_macos_notification


def create_supervisor(store: Optional[MacOSStore] = None) -> Employee:
    store = store or MacOSStore()

    def run_team_standup() -> str:
        """Run an executive team standup where each AI employee reports their status and domain metrics."""
        events = store.list_events()
        tasks = store.list_tasks(status="pending")
        leads = store.list_leads()
        campaigns = store.list_campaigns()
        manuscripts = store.list_manuscripts()

        standup = [
            "🏛️ AGNOSTIC AI EMPLOYEE TEAM STANDUP BRIEFING:",
            "==================================================",
            f"⏱️ Alex (Chief of Staff):",
            f"   • {len(events)} calendar events scheduled. {len(tasks)} pending high-priority tasks.",
            f"   • Next priority: Day structure locked and calendar defended.",
            "",
            f"💼 Morgan (Freelance & BizDev Hunter):",
            f"   • {len(leads)} active deals in CRM pipeline.",
            f"   • Next priority: Pitch proposals and high-ticket client outreach.",
            "",
            f"🚀 Taylor (Growth & Marketing Lead):",
            f"   • {len(campaigns)} marketing campaigns & newsletter drafts logged.",
            f"   • Next priority: Distribution hooks and audience growth.",
            "",
            f"✍️ Elena (High-Empathy Wordsmith & Author):",
            f"   • {len(manuscripts)} manuscript chapters & long-form drafts.",
            f"   • Next priority: Tone calibration, empathetic client comms, and book chapters.",
            "==================================================",
            "All systems active. What would you like your team to tackle right now?"
        ]
        send_macos_notification("Team Standup Completed", f"{len(tasks)} tasks, {len(leads)} leads active")
        return "\n".join(standup)

    tools = [
        ToolSpec("run_team_standup", "Conduct an executive standup briefing summarizing status across all employees.",
                 {"type": "object", "properties": {}},
                 fn=run_team_standup),
    ]

    prompt = """You are the Executive Supervisor and Team Orchestrator for the user's AI employee team.
Your team consists of:
1. Alex (Chief of Staff & Day Planner): Manages calendar, daily schedule, meetings, task board, and day planning.
2. Morgan (Freelance & BizDev Hunter): Finds freelance clients, writes proposals, handles rate quotes, and manages CRM leads.
3. Taylor (Marketing & Growth Lead): Crafts social media content, viral hooks, newsletters, and marketing campaigns.
4. Elena (High-Empathy Wordsmith & Author): Powered by Claude Haiku 4.5/Sonnet for deeply empathetic communication, difficult emails, and book manuscripts.
5. Jack (Software Engineering Lead): Uses GitHub Copilot for coding, debugging, code review, and test automation.

Your goal is to delegate user requests to the ideal specialist using `delegate_task(target_employee, instruction)`, or run `run_team_standup` when requested.
When a multi-step task requires multiple employees, coordinate them seamlessly (e.g. Jack implements a feature -> Elena polishes the release note -> Alex schedules the follow-up).
Always maintain an executive, poised, supportive tone.
"""

    return Employee(
        name="Supervisor",
        title="Team Orchestrator & Operations Director",
        role="Multi-Agent Orchestration, Delegation, Standups & Executive Coordination",
        route="default",
        voice="Samantha",
        avatar="👑",
        system_prompt=prompt,
        tools=tools,
        store=store,
    )

