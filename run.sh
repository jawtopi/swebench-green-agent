#!/bin/bash
# AgentBeats controller will set $HOST, $AGENT_PORT, $AGENT_ID
# CLOUDRUN_HOST and HTTPS_ENABLED should be set in Railway env vars
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Debug: log environment variables
echo "=== run.sh environment ===" >&2
echo "CLOUDRUN_HOST=$CLOUDRUN_HOST" >&2
echo "AGENT_ID=$AGENT_ID" >&2
echo "HTTPS_ENABLED=$HTTPS_ENABLED" >&2
echo "HOST=$HOST" >&2
echo "AGENT_PORT=$AGENT_PORT" >&2
echo "--- All env vars containing 'AGENT' or 'ID' ---" >&2
env | grep -iE '(agent|id|cagent)' >&2
echo "==========================" >&2

# Activate virtual environment if it exists (local dev)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Construct public URL for agent card
if [ -n "$CLOUDRUN_HOST" ]; then
    if [ "$HTTPS_ENABLED" = "true" ]; then
        PUBLIC_URL="https://${CLOUDRUN_HOST}"
    else
        PUBLIC_URL="http://${CLOUDRUN_HOST}"
    fi
    # Append agent path if AGENT_ID is set
    if [ -n "$AGENT_ID" ]; then
        PUBLIC_URL="${PUBLIC_URL}/to_agent/${AGENT_ID}"
    fi
    echo "Constructed PUBLIC_URL=$PUBLIC_URL" >&2
    python main.py serve --host "${HOST:-0.0.0.0}" --port "${AGENT_PORT:-9001}" --url "$PUBLIC_URL"
else
    echo "No CLOUDRUN_HOST set, using default URL" >&2
    python main.py serve --host "${HOST:-0.0.0.0}" --port "${AGENT_PORT:-9001}"
fi
