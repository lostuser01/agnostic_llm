"""macOS system integrations and persistent data store.
Provides Calendar, Reminders, Notifications, Clipboard, Mail, and persistent SQLite storage.
Handles sandboxed/offline environments gracefully with full local fallback.
"""
from __future__ import annotations
import datetime
import json
import logging
import os
import sqlite3
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("agnostic_llm.macos")

def _default_db_path() -> Path:
    # Check candidates: workspace .data, user home ~/.agnostic_llm, or /tmp
    for candidate in [
        Path.cwd() / ".data" / "data.db",
        Path.home() / ".agnostic_llm" / "data.db",
        Path("/tmp") / ".agnostic_llm" / "data.db",
    ]:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            continue
    return Path("data.db")


DB_PATH = _default_db_path()


def run_applescript(script: str) -> tuple[bool, str]:
    """Execute an AppleScript snippet via osascript. Returns (success, output/error)."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip()
    except Exception as e:
        return False, str(e)


class MacOSStore:
    """Local SQLite store for calendar events, tasks, CRM leads, marketing campaigns, and manuscripts."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes INTEGER DEFAULT 60,
                    location TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    attendees TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    due_date TEXT,
                    category TEXT DEFAULT 'General',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crm_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    project_scope TEXT DEFAULT '',
                    estimated_value TEXT DEFAULT '$0',
                    status TEXT DEFAULT 'lead',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketing_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    platform TEXT DEFAULT 'all',
                    content TEXT NOT NULL,
                    hook TEXT DEFAULT '',
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manuscripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    chapter_number INTEGER DEFAULT 1,
                    summary TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    tone TEXT DEFAULT 'empathetic',
                    word_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def backup_database(self, destination: Path | None = None) -> Path:
        """Create a consistent SQLite backup without exposing the live database file."""
        if destination is None:
            backup_dir = self.db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            destination = backup_dir / f"{self.db_path.stem}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
        destination = Path(destination).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.resolve() == self.db_path.resolve():
            raise ValueError("backup destination must differ from the live database")
        temp_destination = destination.with_name(f".{destination.name}.tmp")
        try:
            with self._get_conn() as source, sqlite3.connect(str(temp_destination)) as target:
                source.backup(target)
                target.commit()
            temp_destination.replace(destination)
        finally:
            temp_destination.unlink(missing_ok=True)
        return destination

    # --- Calendar Methods ---
    def add_event(self, title: str, start_time: str, duration_minutes: int = 60,
                  location: str = "", notes: str = "", attendees: str = "") -> dict:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO calendar_events (title, start_time, duration_minutes, location, notes, attendees)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, start_time, duration_minutes, location, notes, attendees))
            event_id = cur.lastrowid
            conn.commit()

        # Attempt Apple Calendar sync if available
        applescript = f'''
        tell application "Calendar"
            tell calendar 1
                make new event with properties {{summary:"{title}", description:"{notes}", location:"{location}"}}
            end tell
        end tell
        '''
        run_applescript(applescript)

        return {
            "id": event_id,
            "title": title,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "location": location,
            "notes": notes,
            "attendees": attendees,
            "status": "scheduled"
        }

    def list_events(self, date_prefix: Optional[str] = None) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            if date_prefix:
                cur.execute("SELECT * FROM calendar_events WHERE start_time LIKE ? ORDER BY start_time ASC", (f"{date_prefix}%",))
            else:
                cur.execute("SELECT * FROM calendar_events ORDER BY start_time ASC")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    # --- Task Methods ---
    def create_task(self, title: str, priority: str = "medium", due_date: Optional[str] = None, category: str = "General") -> dict:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO tasks (title, priority, due_date, category, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (title, priority.lower(), due_date or "", category))
            task_id = cur.lastrowid
            conn.commit()

        # Attempt Apple Reminders sync
        applescript = f'''
        tell application "Reminders"
            tell default list
                make new reminder with properties {{name:"{title}", body:"Priority: {priority}"}}
            end tell
        end tell
        '''
        run_applescript(applescript)

        return {"id": task_id, "title": title, "priority": priority, "due_date": due_date, "category": category, "status": "pending"}

    def list_tasks(self, status: str = "pending", category: Optional[str] = None) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            if status != "all":
                query += " AND status = ?"
                params.append(status)
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id DESC"
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def complete_task(self, task_id_or_title: str | int) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            if str(task_id_or_title).isdigit():
                cur.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (int(task_id_or_title),))
            else:
                cur.execute("UPDATE tasks SET status = 'completed' WHERE title LIKE ?", (f"%{task_id_or_title}%",))
            changed = cur.rowcount > 0
            conn.commit()
            return changed

    # --- CRM Lead Methods ---
    def add_lead(self, client_name: str, company: str = "", project_scope: str = "",
                 estimated_value: str = "$0", status: str = "lead", notes: str = "") -> dict:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO crm_leads (client_name, company, project_scope, estimated_value, status, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (client_name, company, project_scope, estimated_value, status.lower(), notes))
            lead_id = cur.lastrowid
            conn.commit()
            return {"id": lead_id, "client_name": client_name, "company": company, "project_scope": project_scope,
                    "estimated_value": estimated_value, "status": status, "notes": notes}

    def list_leads(self, status: str = "all") -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            if status != "all":
                cur.execute("SELECT * FROM crm_leads WHERE status = ? ORDER BY id DESC", (status.lower(),))
            else:
                cur.execute("SELECT * FROM crm_leads ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    def update_lead(self, lead_id: int, status: Optional[str] = None, notes: Optional[str] = None) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            updates = []
            params = []
            if status:
                updates.append("status = ?")
                params.append(status.lower())
            if notes:
                updates.append("notes = ?")
                params.append(notes)
            if not updates:
                return False
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(lead_id)
            cur.execute(f"UPDATE crm_leads SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return cur.rowcount > 0

    # --- Marketing & Content Methods ---
    def save_campaign(self, title: str, content: str, platform: str = "all", hook: str = "", status: str = "draft") -> dict:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO marketing_campaigns (title, content, platform, hook, status)
                VALUES (?, ?, ?, ?, ?)
            """, (title, content, platform, hook, status))
            item_id = cur.lastrowid
            conn.commit()
            return {"id": item_id, "title": title, "platform": platform, "hook": hook, "status": status}

    def list_campaigns(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM marketing_campaigns ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    # --- Manuscripts & Empathy Content ---
    def save_manuscript(self, title: str, content: str, chapter_number: int = 1,
                        summary: str = "", tone: str = "empathetic") -> dict:
        word_count = len(content.split())
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO manuscripts (title, chapter_number, summary, content, tone, word_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (title, chapter_number, summary, content, tone, word_count))
            item_id = cur.lastrowid
            conn.commit()
            return {"id": item_id, "title": title, "chapter_number": chapter_number, "word_count": word_count, "tone": tone}

    def list_manuscripts(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, title, chapter_number, summary, tone, word_count, updated_at FROM manuscripts ORDER BY chapter_number ASC, id ASC")
            return [dict(r) for r in cur.fetchall()]

    def get_manuscript(self, manuscript_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM manuscripts WHERE id = ?", (manuscript_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # --- Memory Store ---
    def remember(self, employee_name: str, key: str, value: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO employee_memories (employee_name, key, value)
                VALUES (?, ?, ?)
            """, (employee_name.lower(), key, value))
            conn.commit()

    def recall(self, employee_name: str, key: Optional[str] = None) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            if key:
                cur.execute("SELECT * FROM employee_memories WHERE employee_name = ? AND key = ? ORDER BY id DESC", (employee_name.lower(), key))
            else:
                cur.execute("SELECT * FROM employee_memories WHERE employee_name = ? ORDER BY id DESC LIMIT 20", (employee_name.lower(),))
            return [dict(r) for r in cur.fetchall()]


# In-memory clipboard fallback
_INTERNAL_CLIPBOARD = ""


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS system clipboard using pbcopy, with fallback to in-memory store."""
    global _INTERNAL_CLIPBOARD
    _INTERNAL_CLIPBOARD = text
    try:
        proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, timeout=3)
        return proc.returncode == 0
    except Exception as e:
        log.debug("pbcopy fallback to internal memory: %s", e)
        return True


def get_clipboard() -> str:
    """Retrieve text from macOS system clipboard using pbpaste, with internal fallback."""
    global _INTERNAL_CLIPBOARD
    try:
        proc = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    except Exception as e:
        log.debug("pbpaste fallback: %s", e)
    return _INTERNAL_CLIPBOARD


def send_macos_notification(title: str, message: str, subtitle: str = "") -> bool:
    """Deliver a native macOS notification alert via AppleScript."""
    clean_title = title.replace('"', '\\"')
    clean_msg = message.replace('"', '\\"')
    clean_sub = subtitle.replace('"', '\\"')
    sub_clause = f' subtitle "{clean_sub}"' if clean_sub else ""
    script = f'display notification "{clean_msg}" with title "{clean_title}"{sub_clause}'
    ok, _ = run_applescript(script)
    if not ok:
        # Fallback to terminal bell or log
        log.info("[Notification] %s: %s", title, message)
    return ok


def open_draft_in_apple_mail(recipient: str, subject: str, body: str) -> bool:
    """Create a new outgoing message draft in Apple Mail."""
    clean_subj = subject.replace('"', '\\"')
    clean_body = body.replace('"', '\\"').replace("\n", "\\n")
    clean_recip = recipient.replace('"', '\\"')
    script = f'''
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{subject:"{clean_subj}", content:"{clean_body}", visible:true}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{clean_recip}"}}
        end tell
        activate
    end tell
    '''
    ok, _ = run_applescript(script)
    return ok
