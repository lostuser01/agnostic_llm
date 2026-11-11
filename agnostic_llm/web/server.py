"""Fast Starlette web server powering the macOS desktop web application and voice interface."""
from __future__ import annotations
import json
import logging
from pathlib import Path
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
import uvicorn

from ..employees import EmployeeRoster
from ..voice import voice_engine
from ..macos import MacOSStore, copy_to_clipboard, get_clipboard

log = logging.getLogger("agnostic_llm.web")

STATIC_DIR = Path(__file__).parent / "static"


def create_app(config_path: str = "config.yaml") -> Starlette:
    store = MacOSStore()
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
        t = store.create_task(
            title=data.get("title", "New Task"),
            priority=data.get("priority", "medium"),
            due_date=data.get("due_date"),
            category=data.get("category", "General"),
        )
        return JSONResponse({"success": True, "task": t})

    async def complete_task(request: Request):
        data = await request.json()
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

    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]

    return Starlette(debug=True, routes=routes, middleware=middleware)


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

