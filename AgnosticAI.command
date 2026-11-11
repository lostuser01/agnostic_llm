#!/bin/bash
# Agnostic AI — macOS Desktop Launcher
# Double-click to start your autonomous AI employee army & voice dashboard.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🍎 Launching Agnostic AI — Autonomous Employee Army"
echo "=========================================================="

# Select Python binary
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    read -p "Press enter to exit..."
    exit 1
fi

export PYTHONPATH="$DIR:$PYTHONPATH"

# Open default browser after 1.5 seconds
(sleep 1.5 && open "http://127.0.0.1:8000") &

# Start Web Server & Voice Interface
$PY -m agnostic_llm --web --port 8000

