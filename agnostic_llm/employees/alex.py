"""Alex: Chief of Staff & Productivity Lead.
Specializes in day planning, schedule management, time blocking, task priorities,
meeting bookings, and morning/evening executive briefings on macOS.
"""
from __future__ import annotations
import datetime
import json
from typing import Optional
from .base import Employee
from ..types import ToolSpec
from ..macos import MacOSStore, send_macos_notification, copy_to_clipboard


def create_alex(store: Optional[MacOSStore] = None) -> Employee:
    store = store or MacOSStore()

    def get_daily_agenda(date: str = "") -> str:
        """Retrieve scheduled meetings, calendar events, and top priority tasks for a given date (defaults to today)."""
        target_date = date or datetime.date.today().isoformat()
        events = store.list_events(date_prefix=target_date)
        tasks = store.list_tasks(status="pending")

        report = [f"📅 Agenda for {target_date}:"]
        if events:
            report.append("\nScheduled Calendar Events:")
            for ev in events:
                loc = f" ({ev['location']})" if ev.get("location") else ""
                report.append(f"  • {ev['start_time']} - {ev['title']} [{ev['duration_minutes']} min]{loc}")
        else:
            report.append("\nNo calendar events scheduled yet.")

        if tasks:
            report.append("\nPending Tasks:")
            for t in tasks:
                p_badge = f"[{t['priority'].upper()}]"
                report.append(f"  • ID #{t['id']}: {p_badge} {t['title']} (Category: {t['category']})")
        else:
            report.append("\nNo pending tasks.")

        return "\n".join(report)

    def schedule_meeting(
        title: str,
        start_time: str,
        duration_minutes: int = 60,
        location: str = "",
        notes: str = "",
        attendees: str = ""
    ) -> str:
        """Schedule a meeting or calendar event, saving to macOS Calendar and local schedule."""
        ev = store.add_event(
            title=title,
            start_time=start_time,
            duration_minutes=duration_minutes,
            location=location,
            notes=notes,
            attendees=attendees
        )
        send_macos_notification("Meeting Scheduled", f"{title} at {start_time}")
        return f"Successfully scheduled meeting '{title}' for {start_time} ({duration_minutes} min). Event ID #{ev['id']}."

    def create_task(title: str, priority: str = "medium", due_date: str = "", category: str = "General") -> str:
        """Create a new action item or reminder with priority ('high', 'medium', 'low') and due date."""
        t = store.create_task(title=title, priority=priority, due_date=due_date, category=category)
        return f"Task #{t['id']} created: '{title}' [Priority: {priority.upper()}, Category: {category}]."

    def list_tasks(status: str = "pending", category: str = "") -> str:
        """List current tasks filtered by status ('pending', 'completed', 'all') and optional category."""
        items = store.list_tasks(status=status, category=category if category else None)
        if not items:
            return f"No tasks found matching status '{status}'."
        lines = [f"Found {len(items)} task(s):"]
        for t in items:
            lines.append(f"  • #{t['id']} [{t['status'].upper()}] [{t['priority'].upper()}] {t['title']} (Due: {t['due_date'] or 'None'})")
        return "\n".join(lines)

    def complete_task(task_id_or_title: str) -> str:
        """Mark a task as completed by ID or name."""
        ok = store.complete_task(task_id_or_title)
        if ok:
            send_macos_notification("Task Completed", f"Marked task {task_id_or_title} as complete")
            return f"Successfully marked task '{task_id_or_title}' as completed."
        return f"Could not find task '{task_id_or_title}' to mark as completed."

    def plan_my_day(wake_time: str = "08:00", sleep_time: str = "23:00", priorities: str = "") -> str:
        """Generate an optimized daily time-blocking schedule with deep work blocks, breaks, and buffer time."""
        existing_agenda = get_daily_agenda()
        plan = f"""
Daily Master Plan:
- Operating Window: {wake_time} to {sleep_time}
- Key Priorities: {priorities or 'High-priority task execution & deep focus'}

Schedule Blocks:
• 08:30 - 09:00 | Morning Briefing, Coffee, Quick Inbox Review
• 09:00 - 11:30 | Deep Work Block 1 (High priority creative/client tasks)
• 11:30 - 12:00 | Physical Reset & Buffer / Walk
• 12:00 - 13:00 | Lunch & Recharge
• 13:00 - 15:00 | Deep Work Block 2 (Execution, meetings, outreach)
• 15:00 - 15:30 | Comms & Admin (Elena review, Morgan pipeline)
• 15:30 - 17:30 | Project Delivery & Focus Block 3
• 17:30 - 18:00 | End-of-Day Shutdown & Tomorrow's Priority Lock

Current Context:
{existing_agenda}
"""
        copy_to_clipboard(plan.strip())
        return plan.strip()

    tools = [
        ToolSpec("get_daily_agenda", "Retrieve scheduled meetings, calendar events, and tasks for today or a specific date.",
                 {"type": "object", "properties": {"date": {"type": "string", "description": "Date YYYY-MM-DD or empty for today"}}},
                 fn=get_daily_agenda),
        ToolSpec("schedule_meeting", "Schedule a meeting or calendar event on macOS.",
                 {"type": "object",
                  "properties": {
                      "title": {"type": "string"},
                      "start_time": {"type": "string", "description": "e.g. 2026-11-12 14:00"},
                      "duration_minutes": {"type": "integer"},
                      "location": {"type": "string"},
                      "notes": {"type": "string"},
                      "attendees": {"type": "string"}
                  },
                  "required": ["title", "start_time"]},
                 fn=schedule_meeting),
        ToolSpec("create_task", "Create a new task or reminder with priority and due date.",
                 {"type": "object",
                  "properties": {
                      "title": {"type": "string"},
                      "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                      "due_date": {"type": "string"},
                      "category": {"type": "string"}
                  },
                  "required": ["title"]},
                 fn=create_task),
        ToolSpec("list_tasks", "List current tasks filtered by status and category.",
                 {"type": "object",
                  "properties": {
                      "status": {"type": "string", "enum": ["pending", "completed", "all"]},
                      "category": {"type": "string"}
                  }},
                 fn=list_tasks),
        ToolSpec("complete_task", "Mark a task complete by ID or title.",
                 {"type": "object",
                  "properties": {"task_id_or_title": {"type": "string"}},
                  "required": ["task_id_or_title"]},
                 fn=complete_task),
        ToolSpec("plan_my_day", "Generate an optimized daily time-blocking schedule and copy to clipboard.",
                 {"type": "object",
                  "properties": {
                      "wake_time": {"type": "string"},
                      "sleep_time": {"type": "string"},
                      "priorities": {"type": "string"}
                  }},
                 fn=plan_my_day),
    ]

    prompt = """You are Alex, Chief of Staff & Productivity Lead.
Your mission is to maximize the user's executive leverage, preserve their focus, and ensure flawless daily execution.
You manage the calendar, day plans, meeting schedules, and task priorities.
When asked to plan the day, look at existing events and pending tasks, eliminate friction, and construct realistic time blocks.
Be concise, proactive, highly organized, and always give crisp summaries.
"""

    return Employee(
        name="Alex",
        title="Chief of Staff & Day Planner",
        role="Productivity, Calendar Management, Day Planning & Task Execution",
        route="default",
        voice="Samantha",
        avatar="⏱️",
        system_prompt=prompt,
        tools=tools,
        store=store,
    )
