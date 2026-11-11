#!/usr/bin/env bash
# Agnostic AI — macOS CLI & Service Runner
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
export PYTHONPATH="$DIR:$PYTHONPATH"

MODE="${1:---web}"

case "$MODE" in
    --web|-w)
        echo "🍎 Starting Agnostic AI Web Dashboard & Voice Studio on http://127.0.0.1:8000..."
        (sleep 1 && open "http://127.0.0.1:8000" 2>/dev/null || true) &
        python3 -m agnostic_llm --web --port 8000
        ;;
    --cli|-c)
        echo "🍎 Starting Agnostic AI Terminal Assistant..."
        python3 -m agnostic_llm "${@:2}"
        ;;
    --voice|-v)
        echo "🍎 Starting Hands-Free macOS Voice Mode..."
        python3 -m agnostic_llm --voice "${@:2}"
        ;;
    --standup|-s)
        echo "🍎 Running Morning Executive Standup..."
        python3 -m agnostic_llm --standup
        ;;
    *)
        python3 -m agnostic_llm "$@"
        ;;
esac

