#!/bin/bash
# AgentBeats controller will set $HOST and $AGENT_PORT
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists (local dev)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python main.py serve --host "${HOST:-0.0.0.0}" --port "${AGENT_PORT:-9001}"
