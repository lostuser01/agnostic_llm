"""Local authentication, audit logging, and remembered approval policies."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class SecurityStore:
    """SQLite-backed security state for the local single-user dashboard."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    github_id TEXT NOT NULL,
                    login TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state_hash TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT DEFAULT '',
                    details TEXT DEFAULT '{}',
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approval_policies (
                    action TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at INTEGER NOT NULL,
                    resolved_at INTEGER
                );
                """
            )

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create_oauth_state(self, ttl_seconds: int = 600) -> str:
        state = secrets.token_urlsafe(32)
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO oauth_states VALUES (?, ?, ?)",
                (self._hash(state), now, now + ttl_seconds),
            )
        return state

    def consume_oauth_state(self, state: str) -> bool:
        now = int(time.time())
        state_hash = self._hash(state)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT expires_at FROM oauth_states WHERE state_hash = ?",
                (state_hash,),
            ).fetchone()
            conn.execute("DELETE FROM oauth_states WHERE state_hash = ?", (state_hash,))
        return bool(row and row["expires_at"] >= now)

    def create_session(self, github_id: str, login: str, ttl_seconds: int = 86400) -> str:
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?)",
                (self._hash(token), str(github_id), login, now, now + ttl_seconds),
            )
        return token

    def get_session(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT github_id, login, expires_at FROM auth_sessions WHERE token_hash = ?",
                (self._hash(token),),
            ).fetchone()
        if not row or row["expires_at"] < int(time.time()):
            return None
        return dict(row)

    def revoke_session(self, token: str | None):
        if token:
            with self._connect() as conn:
                conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (self._hash(token),))

    def audit(self, actor: str, action: str, resource: str = "", details: dict | None = None):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (actor, action, resource, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (actor, action, resource, json.dumps(details or {}), int(time.time())),
            )

    def set_approval(self, action: str, decision: str):
        if decision not in {"allow", "deny", "ask"}:
            raise ValueError("approval decision must be allow, deny, or ask")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO approval_policies VALUES (?, ?, ?)",
                (action, decision, int(time.time())),
            )

    def get_approval(self, action: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT decision FROM approval_policies WHERE action = ?", (action,)
            ).fetchone()
        return row["decision"] if row else "ask"

    def list_approvals(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT action, decision, updated_at FROM approval_policies ORDER BY action"
            ).fetchall()
        return [dict(row) for row in rows]

    def create_approval_request(self, actor: str, action: str, details: dict | None = None) -> str:
        request_id = secrets.token_urlsafe(18)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO approval_requests (id, actor, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (request_id, actor, action, json.dumps(details or {}), int(time.time())),
            )
        return request_id

    def list_pending_approvals(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, actor, action, details, created_at FROM approval_requests "
                "WHERE status = 'pending' ORDER BY created_at ASC"
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item["details"])
            result.append(item)
        return result

    def resolve_approval(self, request_id: str, decision: str, remember: bool = True) -> bool:
        if decision not in {"allow", "deny"}:
            raise ValueError("approval decision must be allow or deny")
        now = int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                "SELECT action FROM approval_requests WHERE id = ? AND status = 'pending'",
                (request_id,),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "UPDATE approval_requests SET status = ?, resolved_at = ? WHERE id = ?",
                (decision, now, request_id),
            )
            if remember:
                conn.execute(
                    "INSERT OR REPLACE INTO approval_policies VALUES (?, ?, ?)",
                    (row["action"], decision, now),
                )
        return True


class ApprovalRequired(Exception):
    """Raised when a tool needs an explicit user decision before execution."""

    def __init__(self, request_id: str, action: str, details: dict):
        super().__init__(f"Approval required for {action} (request {request_id})")
        self.request_id = request_id
        self.action = action
        self.details = details


def github_authorize_url(state: str) -> str:
    client_id = os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")
    redirect_uri = os.environ.get(
        "GITHUB_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback"
    )
    query = urllib.parse.urlencode(
        {"client_id": client_id, "redirect_uri": redirect_uri, "scope": "read:user user:email", "state": state}
    )
    return f"https://github.com/login/oauth/authorize?{query}"


def exchange_github_code(code: str) -> dict[str, Any]:
    client_id = os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET are required")
    payload = urllib.parse.urlencode(
        {"client_id": client_id, "client_secret": client_secret, "code": code}
    ).encode()
    request = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=payload,
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        token_data = json.loads(response.read().decode("utf-8"))
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError(token_data.get("error_description", "GitHub OAuth token exchange failed"))

    user_request = urllib.request.Request(
        "https://api.github.com/user",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(user_request, timeout=15) as response:
        user = json.loads(response.read().decode("utf-8"))
    return {"id": str(user["id"]), "login": user["login"]}
