"""Fast Starlette web server powering the macOS desktop web application and voice interface."""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
import uvicorn

from ..employees import EmployeeRoster
from ..voice import voice_engine
from ..macos import MacOSStore, copy_to_clipboard, get_clipboard
from ..security import ApprovalRequired, SecurityStore, exchange_github_code, github_authorize_url

log = logging.getLogger("agnostic_llm.web")

STATIC_DIR = Path(__file__).parent / "static"


def create_app(config_path: str = "config.yaml") -> Starlette:
    store = MacOSStore()
    security = SecurityStore(store.db_path)
    auth_required = os.environ.get("AGNOSTIC_AUTH_REQUIRED", "1") != "0"
    allowed_origin = os.environ.get("AGNOSTIC_ALLOWED_ORIGIN", "http://127.0.0.1:8000")
    try:
        roster = EmployeeRoster.from_config(config_path, store=store)
    except Exception as e:
        log.warning("Could not load config '%s', using default roster: %s", config_path, e)
        roster = EmployeeRoster(store=store)

    async def index(request: Request):
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Agnostic AI: macOS Employee Suite</h1>")

    async def auth_login(request: Request):
        if not os.environ.get("GITHUB_OAUTH_CLIENT_ID"):
            return HTMLResponse(
                "<h1>GitHub OAuth is not configured</h1>"
                "<p>Set GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET.</p>",
                status_code=503,
            )
        state = security.create_oauth_state()
        return RedirectResponse(github_authorize_url(state), status_code=303)

    async def auth_callback(request: Request):
        state = request.query_params.get("state", "")
        code = request.query_params.get("code", "")
        if not state or not security.consume_oauth_state(state):
            return HTMLResponse("<h1>Invalid or expired OAuth state</h1>", status_code=400)
        try:
            user = exchange_github_code(code)
            token = security.create_session(user["id"], user["login"])
            security.audit(user["login"], "auth.login")
            response = RedirectResponse("/", status_code=303)
            response.set_cookie(
                "agnostic_session",
                token,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
                max_age=86400,
            )
            return response
        except Exception as exc:
            log.exception("GitHub OAuth callback failed")
            return HTMLResponse(f"<h1>Authentication failed</h1><p>{exc}</p>", status_code=502)

    async def auth_logout(request: Request):
        token = request.cookies.get("agnostic_session")
        session = security.get_session(token)
        if session:
            security.audit(session["login"], "auth.logout")
        security.revoke_session(token)
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("agnostic_session")
        return response

    async def current_user(request: Request):
        session = security.get_session(request.cookies.get("agnostic_session"))
        return JSONResponse({"authenticated": bool(session), "user": session})

    async def get_approvals(request: Request):
        return JSONResponse({"approvals": security.list_pending_approvals(), "policies": security.list_approvals()})

    async def resolve_approval(request: Request):
        data = await request.json()
        ok = security.resolve_approval(
            str(data.get("id", "")),
            data.get("decision", "deny"),
            bool(data.get("remember", True)),
        )
        session = security.get_session(request.cookies.get("agnostic_session"))
        if session:
            security.audit(session["login"], "approval.resolve", str(data.get("id", "")), data)
        return JSONResponse({"success": ok}, status_code=200 if ok else 404)

    def require_api_approval(request: Request, action: str, details: dict):
        session = security.get_session(request.cookies.get("agnostic_session"))
        actor = session["login"] if session else "anonymous"
        decision = security.get_approval(action)
        if decision == "allow":
            security.audit(actor, "api.approved", action, details)
            return None
        if decision == "deny":
            security.audit(actor, "api.denied", action, details)
            return JSONResponse({"success": False, "error": "action_denied", "action": action}, status_code=403)
        request_id = security.create_approval_request(actor, action, details)
        return JSONResponse({
            "success": False,
            "error": "approval_required",
            "request_id": request_id,
            "action": action,
            "details": details,
        }, status_code=409)

    async def get_workspaces(request: Request):
        return JSONResponse({"workspaces": security.list_workspaces()})

    async def allow_workspace(request: Request):
        data = await request.json()
        path = str(data.get("path", "")).strip()
        if not path:
            return JSONResponse({"success": False, "error": "path_required"}, status_code=400)
        approval = require_api_approval(request, "workspace.allow", {"path": path})
        if approval:
            return approval
        security.allow_workspace(path)
        return JSONResponse({"success": True, "workspaces": security.list_workspaces()})

    async def revoke_workspace(request: Request):
        data = await request.json()
        path = str(data.get("path", "")).strip()
        approval = require_api_approval(request, "workspace.revoke", {"path": path})
        if approval:
            return approval
        security.revoke_workspace(path)
        return JSONResponse({"success": True, "workspaces": security.list_workspaces()})

    async def get_employees(request: Request):
        emps = []
        for e in roster.list_all():
            emps.append({
                "name": e.name,
                "title": e.title,
                "role": e.role,
                "route": e.route,
                "voice": e.voice,
                "avatar": e.avatar,
                "tools_count": len(e.tools),
            })
        return JSONResponse({"employees": emps})

    async def chat_handler(request: Request):
        data = await request.json()
        emp_name = data.get("employee", "supervisor")
        prompt = data.get("prompt", "")
        voice_out = data.get("voice_out", False)

        emp = roster.get(emp_name) or roster.get("supervisor")
        try:
            session = security.get_session(request.cookies.get("agnostic_session"))
            security.audit(session["login"] if session else "anonymous", "employee.chat", emp.name)
            res = emp.chat(prompt)
            # Spoken voice output via macOS say if requested
            if voice_out:
                voice_engine.speak(res.text, voice=emp.voice, employee_name=emp.name)

            tool_calls_data = []
            for tc in res.tool_calls:
                tool_calls_data.append({
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                })

            return JSONResponse({
                "success": True,
                "employee": emp.name,
                "title": emp.title,
                "avatar": emp.avatar,
                "text": res.text,
                "tool_calls": tool_calls_data,
                "voice": emp.voice,
            })
        except ApprovalRequired as exc:
            return JSONResponse({
                "success": False,
                "error": "approval_required",
                "request_id": exc.request_id,
                "action": exc.action,
                "details": exc.details,
            }, status_code=409)
        except Exception as e:
            log.exception("Chat execution error: %s", e)
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

    # --- Agenda & Calendar APIs ---
    async def get_agenda(request: Request):
        date_param = request.query_params.get("date")
        events = store.list_events(date_prefix=date_param)
        tasks = store.list_tasks(status="all")
        return JSONResponse({"events": events, "tasks": tasks})

    async def create_event(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "calendar.schedule", data)
        if approval:
            return approval
        ev = store.add_event(
            title=data.get("title", "New Event"),
            start_time=data.get("start_time", ""),
            duration_minutes=int(data.get("duration_minutes", 60)),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            attendees=data.get("attendees", ""),
        )
        return JSONResponse({"success": True, "event": ev})

    # --- Task APIs ---
    async def get_tasks(request: Request):
        status = request.query_params.get("status", "pending")
        category = request.query_params.get("category")
        tasks = store.list_tasks(status=status, category=category)
        return JSONResponse({"tasks": tasks})

    async def create_task(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "tasks.create", data)
        if approval:
            return approval
        t = store.create_task(
            title=data.get("title", "New Task"),
            priority=data.get("priority", "medium"),
            due_date=data.get("due_date"),
            category=data.get("category", "General"),
        )
        return JSONResponse({"success": True, "task": t})

    async def complete_task(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "tasks.complete", data)
        if approval:
            return approval
        task_id = data.get("id")
        ok = store.complete_task(task_id)
        return JSONResponse({"success": ok})

    # --- CRM Leads APIs ---
    async def get_leads(request: Request):
        status = request.query_params.get("status", "all")
        leads = store.list_leads(status=status)
        return JSONResponse({"leads": leads})

    async def create_lead(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "crm.lead.create", data)
        if approval:
            return approval
        lead = store.add_lead(
            client_name=data.get("client_name", ""),
            company=data.get("company", ""),
            project_scope=data.get("project_scope", ""),
            estimated_value=data.get("estimated_value", "$0"),
            status=data.get("status", "lead"),
            notes=data.get("notes", ""),
        )
        return JSONResponse({"success": True, "lead": lead})

    async def update_lead(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "crm.lead.update", data)
        if approval:
            return approval
        lead_id = int(data.get("id", 0))
        ok = store.update_lead(
            lead_id=lead_id,
            status=data.get("status"),
            notes=data.get("notes"),
        )
        return JSONResponse({"success": ok})

    # --- Marketing Campaigns APIs ---
    async def get_campaigns(request: Request):
        campaigns = store.list_campaigns()
        return JSONResponse({"campaigns": campaigns})

    async def create_campaign(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "marketing.campaign.save", data)
        if approval:
            return approval
        camp = store.save_campaign(
            title=data.get("title", ""),
            content=data.get("content", ""),
            platform=data.get("platform", "all"),
            hook=data.get("hook", ""),
        )
        return JSONResponse({"success": True, "campaign": camp})

    # --- Manuscripts & Empathy Studio APIs ---
    async def get_manuscripts(request: Request):
        manuscripts = store.list_manuscripts()
        return JSONResponse({"manuscripts": manuscripts})

    async def create_manuscript(request: Request):
        data = await request.json()
        approval = require_api_approval(request, "manuscript.chapter.save", data)
        if approval:
            return approval
        m = store.save_manuscript(
            title=data.get("title", "Untitled Chapter"),
            content=data.get("content", ""),
            chapter_number=int(data.get("chapter_number", 1)),
            summary=data.get("summary", ""),
            tone=data.get("tone", "empathetic"),
        )
        return JSONResponse({"success": True, "manuscript": m})

    # --- Voice & System APIs ---
    async def voice_speak(request: Request):
        data = await request.json()
        text = data.get("text", "")
        voice = data.get("voice")
        employee_name = data.get("employee")
        ok = voice_engine.speak(text, voice=voice, employee_name=employee_name)
        return JSONResponse({"success": ok})

    async def voice_stop(request: Request):
        voice_engine.stop_speaking()
        return JSONResponse({"success": True})

    async def clipboard_copy(request: Request):
        data = await request.json()
        text = data.get("text", "")
        ok = copy_to_clipboard(text)
        return JSONResponse({"success": ok})

    routes = [
        Route("/", endpoint=index, methods=["GET"]),
        Route("/auth/login", endpoint=auth_login, methods=["GET"]),
        Route("/auth/callback", endpoint=auth_callback, methods=["GET"]),
        Route("/auth/logout", endpoint=auth_logout, methods=["GET"]),
        Route("/api/me", endpoint=current_user, methods=["GET"]),
        Route("/api/approvals", endpoint=get_approvals, methods=["GET"]),
        Route("/api/approvals/resolve", endpoint=resolve_approval, methods=["POST"]),
        Route("/api/workspaces", endpoint=get_workspaces, methods=["GET"]),
        Route("/api/workspaces/allow", endpoint=allow_workspace, methods=["POST"]),
        Route("/api/workspaces/revoke", endpoint=revoke_workspace, methods=["POST"]),
        Route("/api/employees", endpoint=get_employees, methods=["GET"]),
        Route("/api/chat", endpoint=chat_handler, methods=["POST"]),
        Route("/api/agenda", endpoint=get_agenda, methods=["GET"]),
        Route("/api/events", endpoint=create_event, methods=["POST"]),
        Route("/api/tasks", endpoint=get_tasks, methods=["GET"]),
        Route("/api/tasks", endpoint=create_task, methods=["POST"]),
        Route("/api/tasks/complete", endpoint=complete_task, methods=["POST"]),
        Route("/api/crm/leads", endpoint=get_leads, methods=["GET"]),
        Route("/api/crm/leads", endpoint=create_lead, methods=["POST"]),
        Route("/api/crm/leads/update", endpoint=update_lead, methods=["POST"]),
        Route("/api/marketing/campaigns", endpoint=get_campaigns, methods=["GET"]),
        Route("/api/marketing/campaigns", endpoint=create_campaign, methods=["POST"]),
        Route("/api/manuscripts", endpoint=get_manuscripts, methods=["GET"]),
        Route("/api/manuscripts", endpoint=create_manuscript, methods=["POST"]),
        Route("/api/voice/speak", endpoint=voice_speak, methods=["POST"]),
        Route("/api/voice/stop", endpoint=voice_stop, methods=["POST"]),
        Route("/api/clipboard/copy", endpoint=clipboard_copy, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
    ]

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            public = request.url.path.startswith("/auth/") or request.url.path.startswith("/static/")
            if auth_required and not public:
                session = security.get_session(request.cookies.get("agnostic_session"))
                if not session:
                    if request.url.path.startswith("/api/"):
                        return JSONResponse({"success": False, "error": "authentication_required"}, status_code=401)
                    return RedirectResponse("/auth/login", status_code=303)
            return await call_next(request)

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "same-origin")
            response.headers.setdefault("Content-Security-Policy", "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline'; connect-src 'self'")
            return response

    middleware = [
        Middleware(SecurityHeadersMiddleware),
        Middleware(AuthMiddleware),
        Middleware(CORSMiddleware, allow_origins=[allowed_origin], allow_methods=["GET", "POST"], allow_headers=["Content-Type"], allow_credentials=True),
    ]

    return Starlette(debug=False, routes=routes, middleware=middleware)


def launch_server(config_path: str = "config.yaml", host: str = "127.0.0.1", port: int = 8000):
    """Launch the uvicorn ASGI server and print access instructions."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app = create_app(config_path)
    print("=" * 65)
    print(f"🍎 AGNOSTIC AI: macOS Employee Army & Voice Suite")
    print(f"Web Dashboard & Voice Interface: http://{host}:{port}")
    print(f"Configuration: {config_path}")
    print("Press Ctrl+C to stop.")
    print("=" * 65)
    uvicorn.run(app, host=host, port=port, log_level="info")

