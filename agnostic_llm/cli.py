"""Interactive CLI for Agnostic AI Employee Army.
Supports interactive employee chat, hands-free macOS voice mode, team standups, and day planning.
"""
from __future__ import annotations
import argparse
import sys
from .employees import EmployeeRoster
from .voice import voice_engine
from .macos import MacOSStore


def main():
    parser = argparse.ArgumentParser(description="Agnostic AI: Autonomous Employee Army & macOS Assistant")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to config file")
    parser.add_argument("-e", "--employee", default="supervisor", help="Employee to speak with (alex, morgan, taylor, elena, supervisor)")
    parser.add_argument("-v", "--voice", action="store_true", help="Enable spoken voice output via macOS say")
    parser.add_argument("--standup", action="store_true", help="Run morning executive team standup")
    parser.add_argument("--agenda", action="store_true", help="Show today's agenda and pending tasks")
    parser.add_argument("--web", action="store_true", help="Launch the macOS Web Dashboard and Voice Server")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default: 8000)")
    parser.add_argument("prompt", nargs="*", help="Optional one-shot prompt")

    args = parser.parse_args()

    # Launch Web Server if requested
    if args.web:
        from .web.server import launch_server
        launch_server(config_path=args.config, port=args.port)
        return

    # Load Roster
    try:
        roster = EmployeeRoster.from_config(args.config)
    except Exception as e:
        print(f"Error loading configuration from '{args.config}': {e}")
        roster = EmployeeRoster()

    # Executive Standup
    if args.standup:
        supervisor = roster.get("supervisor")
        res = supervisor.chat("Run team standup", conversation_history=[])
        print("\n" + res.text + "\n")
        if args.voice:
            voice_engine.speak(res.text, voice=supervisor.voice, wait=True)
        return

    # Daily Agenda
    if args.agenda:
        alex = roster.get("alex")
        res = alex.chat("Show me today's agenda and pending tasks", conversation_history=[])
        print("\n" + res.text + "\n")
        if args.voice:
            voice_engine.speak(res.text, voice=alex.voice, wait=True)
        return

    # Resolve Employee
    emp = roster.get(args.employee)
    if not emp:
        print(f"Unknown employee '{args.employee}'. Available: {[e.name for e in roster.list_all()]}")
        emp = roster.get("supervisor")

    # One-shot prompt
    if args.prompt:
        user_input = " ".join(args.prompt)
        print(f"\n[{emp.name} ({emp.title})]: Thinking...\n")
        res = emp.chat(user_input)
        print(f"{emp.avatar} {emp.name}> {res.text}\n")
        if args.voice:
            voice_engine.speak(res.text, voice=emp.voice, wait=True)
        return

    # Interactive Chat Loop
    print("=" * 65)
    print(f"🍎 AGNOSTIC AI EMPLOYEE ARMY — {emp.name.upper()} ({emp.title})")
    print(f"Voice Output: {'ENABLED (' + emp.voice + ')' if args.voice else 'DISABLED (pass --voice to enable)'}")
    print("Commands: /switch <name>, /standup, /agenda, /voice, /exit")
    print("=" * 65 + "\n")

    while True:
        try:
            user_input = input(f"You > ").strip()
            if not user_input:
                continue

            if user_input in ("/exit", "/quit", "exit", "quit"):
                print("Session ended.")
                break

            if user_input.startswith("/switch"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_emp = roster.get(parts[1])
                    if new_emp:
                        emp = new_emp
                        print(f"Switched to {emp.name} ({emp.title})\n")
                    else:
                        print(f"Available employees: {[e.name for e in roster.list_all()]}\n")
                continue

            if user_input == "/standup":
                res = roster.get("supervisor").chat("Run team standup", conversation_history=[])
                print(f"\n{res.text}\n")
                if args.voice:
                    voice_engine.speak(res.text, voice=roster.get("supervisor").voice)
                continue

            if user_input == "/agenda":
                res = roster.get("alex").chat("Get daily agenda", conversation_history=[])
                print(f"\n{res.text}\n")
                if args.voice:
                    voice_engine.speak(res.text, voice=roster.get("alex").voice)
                continue

            if user_input == "/voice":
                args.voice = not args.voice
                print(f"Voice output is now {'ENABLED' if args.voice else 'DISABLED'}\n")
                continue

            res = emp.chat(user_input)
            print(f"\n{emp.avatar} {emp.name}> {res.text}\n")

            if args.voice:
                voice_engine.speak(res.text, voice=emp.voice, employee_name=emp.name)

        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break


if __name__ == "__main__":
    main()

