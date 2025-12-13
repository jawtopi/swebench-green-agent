#!/bin/bash
# AgentBeats controller will set $HOST, $AGENT_PORT, $AGENT_ID
# CLOUDRUN_HOST and HTTPS_ENABLED should be set in Railway env vars
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists (local dev)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Construct public URL for agent card
if [ -n "$CLOUDRUN_HOST" ] && [ -n "$AGENT_ID" ]; then
    if [ "$HTTPS_ENABLED" = "true" ]; then
        PUBLIC_URL="https://${CLOUDRUN_HOST}/to_agent/${AGENT_ID}"
    else
        PUBLIC_URL="http://${CLOUDRUN_HOST}/to_agent/${AGENT_ID}"
    fi
    python main.py serve --host "${HOST:-0.0.0.0}" --port "${AGENT_PORT:-9001}" --url "$PUBLIC_URL"
else
    python main.py serve --host "${HOST:-0.0.0.0}" --port "${AGENT_PORT:-9001}"
fi
