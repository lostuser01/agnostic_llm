# Agnostic AI — macOS Autonomous Employee Army & Voice Suite

Transform single-model scripts into a full-scale, **macOS-supported executive employee army** with **two-way voice chat**, calendar/task synchronization, freelance client acquisition, growth marketing, and high-empathy communication powered by models like **Claude Haiku 4.5**, **Claude Sonnet 3.7**, **GPT-4o**, and **Gemini Flash**.

---

## Requirements

- Python 3.10 or newer (Python 3.11+ is required for the GitHub Copilot SDK)
- macOS for native voice, AppleScript, Calendar, Reminders, Mail, notifications, and clipboard integration
- At least one configured model provider, or the built-in `mock` route for local testing
- A browser with Web Speech API support (Chrome or Safari) for microphone input

The core library and tests also run on non-macOS systems. Native macOS actions automatically fall back to local SQLite, logging, or in-memory clipboard behavior when unavailable.

## ⚡ Install and Quick Start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all,copilot]"
cp config.example.yaml config.yaml
```

Edit `config.yaml` and export the API keys for the providers you want to use:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"
export GITHUB_TOKEN="your-github-token"
```

Only keys referenced by the routes you use are required. The `mock` provider does not need a key and is useful for testing the UI and tool plumbing.

### GitHub Copilot provider

The `copilot` provider uses GitHub's official `github-copilot-sdk` to run Copilot CLI sessions. Install the project with Python 3.11 or newer, install the Copilot runtime, and authenticate with either a supported `GITHUB_TOKEN` or an existing Copilot CLI login:

```bash
python -m pip install -e ".[copilot]"
python -m copilot download-runtime
gh auth login
```

The default and employee routes try `github-copilot` first, then fall back to the configured providers. To use a different Copilot model, change `models.github-copilot.model` in `config.yaml`. The SDK supports model names exposed by your Copilot CLI installation, such as `gpt-5`.

### Launch the dashboard

```bash
# Start the macOS web dashboard and voice studio
./run_macos.sh

# Or use the installed console command
agnostic-ai --web --port 8000

# Or start directly with Python
python3 -m agnostic_llm --web --port 8000
```

Open <http://127.0.0.1:8000> if it does not open automatically. You can also double-click `AgnosticAI.command` in Finder.

For the production-style local dashboard, create a GitHub OAuth App with callback URL
`http://127.0.0.1:8000/auth/callback`, then configure:

```bash
export GITHUB_OAUTH_CLIENT_ID="..."
export GITHUB_OAUTH_CLIENT_SECRET="..."
export GITHUB_OAUTH_REDIRECT_URI="http://127.0.0.1:8000/auth/callback"
```

The dashboard then requires GitHub login, stores only a hashed session token locally,
and records authentication and employee actions in the SQLite audit log. Set
`AGNOSTIC_AUTH_REQUIRED=0` only for isolated development without OAuth.

The dashboard defaults to localhost-only CORS, security headers, and non-debug mode.
If you intentionally serve it from another local origin, set
`AGNOSTIC_ALLOWED_ORIGIN` to that exact origin. Dashboard mutations use the same
remembered approval policies as employee tools, and browser mutations use CSRF
tokens. Requests are limited to 1 MiB by default and protected by a basic
in-process rate limiter; customize these with `AGNOSTIC_MAX_BODY_BYTES`,
`AGNOSTIC_RATE_LIMIT`, and `AGNOSTIC_RATE_WINDOW`. The authenticated
`POST /api/backup` endpoint creates a consistent SQLite backup under `.data/backups`
by default and is approval-gated.

### Use the terminal assistant

```bash
# Talk to Elena with spoken macOS voice
python3 -m agnostic_llm -e elena --voice

# Ask Alex for a one-shot plan
python3 -m agnostic_llm -e alex "Plan my day with time blocks"

# Ask Jack to work on the repository with GitHub Copilot
python3 -m agnostic_llm -e jack "Inspect the repo and fix the failing tests"

# Run an executive standup
python3 -m agnostic_llm --standup --voice

# Show today's agenda
python3 -m agnostic_llm --agenda
```

The first request may use a fallback model if an earlier provider is unavailable. Routes are evaluated from left to right in `config.yaml`.

---

## 👥 Meet Your AI Employee Roster

| Employee | Title & Domain | Model Route | macOS Voice | Key Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| 👑 **Supervisor** | **Team Orchestrator** | `default` | *Samantha* | Coordinates team, routes intent, multi-agent delegation, executive standups |
| ⏱️ **Alex** | **Chief of Staff & Day Planner** | `default` / `fast` | *Samantha* | Daily agenda, calendar defense, Apple Calendar & Reminders, time blocking, morning briefings |
| 💼 **Morgan** | **Freelance & BizDev Hunter** | `default` / `reasoning` | *Daniel* | Prospecting freelance clients, $10k cold pitch proposals, value-based rate quotes, CRM pipeline |
| 🚀 **Taylor** | **Growth & Marketing Strategist** | `default` | *Karen* | Viral hook psychology, multi-channel social campaigns (LinkedIn/X), newsletters, content calendars |
| ✍️ **Elena** | **High-Empathy Wordsmith & Author** | `empathy` (*Claude Haiku 4.5 / Sonnet*) | *Moira* | Emotionally intelligent client emails, sensitive negotiations, book manuscripts, Apple Mail drafts |
| 💻 **Jack** | **Software Engineering Lead** | `copilot` (*GitHub Copilot*) | *Alex* | Coding, debugging, code review, repository maintenance, and test automation |

---

## 🎙️ macOS Voice Chat Engine

- **Voice Input (STT)**: Built-in Web Speech API microphone recognition directly in the macOS web dashboard with live animated audio waveforms.
- **Voice Output (TTS)**: Native macOS `say` voice synthesis mapped to specific voice personas per employee (*Samantha*, *Daniel*, *Karen*, *Moira*), with markdown cleaning and non-blocking speech.
- **Hands-Free Mode**: Toggle "macOS Voice" in the top bar to have employees speak their replies aloud.

---

## 🍎 macOS Native Integrations

- **Apple Calendar & Daily Agenda**: Schedule meetings directly into macOS Calendar and retrieve today's schedule.
- **Apple Reminders & Task Board**: Manage high/medium/low priority tasks with one-click completion.
- **Apple Mail Integration**: Compose empathetic emails with Elena and open them directly in Apple Mail drafts.
- **System Clipboard**: All generated proposals, schedules, and manuscripts can be copied to the macOS clipboard with one click (`pbcopy`/`pbpaste`).
- **macOS System Notifications**: Delivers notification banners when tasks are finished or standups conclude.
- **Local SQLite Persistence**: Persistent storage in `~/.agnostic_llm/data.db` (or `./.data/data.db`) ensures everything works offline, in sandbox, and in production.

The application may ask macOS for permission to control Calendar, Reminders, and Mail. Approve those prompts in **System Settings → Privacy & Security → Automation**. If permissions are denied, local SQLite records still remain available.

## 🔌 Employee provider integrations

`agnostic_llm.integrations.providers` defines dependency-free, mockable contracts
for Morgan's read-only research/enrichment, Alex's calendar/tasks, Taylor's
social publishing/analytics, Elena's email/document storage, and Jack's
GitHub repository/PR/CI operations. Employee factories accept provider
instances, so tests and deployments can inject adapters without changing the
agent loop. Defaults are local or disabled and make no external API calls.

Use the existing `EnvironmentCredentialStore` (or macOS Keychain fallback) for
credentials; never put tokens in YAML, prompts, or provider implementations.
Publishing, email sending, document writes, pull requests, and CI runs carry
approval keys and remain blocked until the remembered approval policy permits
them.

---

## 🧪 Validate the installation

```bash
PYTHONPATH=. pytest -q
```

Run the dependency-free demo:

```bash
python examples/demo.py
```

The test suite uses temporary databases and mock models, so it does not make paid API calls.

---

## Troubleshooting

- **Provider unavailable:** install the matching optional dependency with `python -m pip install anthropic`, `python -m pip install openai`, or `python -m pip install -e ".[copilot]"`; then verify the corresponding environment variable or Copilot CLI login.
- **Dashboard import error:** reinstall the project with `python -m pip install -e ".[all]"`; Starlette and Uvicorn are included in the base dependencies.
- **No voice output:** confirm that `say` works in Terminal and that the configured voice is installed. Voice output is macOS-only.
- **No microphone input:** allow browser microphone access and use Chrome or Safari.
- **Unexpected data:** local state is stored in `.data/data.db` when launched from the repository, otherwise in `~/.agnostic_llm/data.db`. Delete the specific database file only if you intentionally want to reset local state.

---

## ⚙️ Configuration & High-Empathy Model Routing

Edit `config.yaml` to specify your preferred model keys and fallback chains:

```yaml
models:
  claude-haiku:
    provider: anthropic
    model: claude-3-5-haiku-20241022      # High empathy, fast, low cost
    api_key_env: ANTHROPIC_API_KEY
  claude-sonnet:
    provider: anthropic
    model: claude-3-7-sonnet-20250219     # Deep nuance & long-form manuscripts
    api_key_env: ANTHROPIC_API_KEY
  gpt-4o:
    provider: openai
    model: gpt-4o                         # Flagship general reasoning
    api_key_env: OPENAI_API_KEY
  gemini-flash:
    provider: openai
    model: gemini-2.0-flash
    base_url: https://generativelanguage.googleapis.com/v1beta/openai/
    api_key_env: GEMINI_API_KEY

routes:
  # Empathetic writing, difficult client emails, negotiations, and book manuscripts
  empathy: [claude-haiku, claude-sonnet, gpt-4o, gemini-flash, mock]
  fast: [gemini-flash, gpt-4o-mini, claude-haiku, mock]
  default: [claude-haiku, gpt-4o, gemini-flash, mock]
```

---

## 💻 Python Library Usage

```python
from agnostic_llm.employees import EmployeeRoster
from agnostic_llm.voice import voice_engine

# Load your full employee roster
roster = EmployeeRoster.from_config("config.yaml")

# Ask Alex to plan your day
alex = roster.get("alex")
res = alex.chat("Plan my day with 3 deep work blocks and schedule a 30-min strategy sync at 2 PM")
print(res.text)

# Ask Elena to calibrate an email with high empathy
elena = roster.get("elena")
res_elena = elena.chat("Refine this email to a client explaining a 2-day delivery adjustment with warmth and reassurance")
print(res_elena.text)

# Speak the result in Elena's voice (Moira)
voice_engine.speak(res_elena.text, voice=elena.voice)
```

---

## 🧪 Testing

Run the full automated test suite:
```bash
PYTHONPATH=. pytest
```
Tests cover model providers, conversions, multi-agent employee tools, macOS persistence, and voice processing.
