#!/usr/bin/env bash
set -e

ABIX_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ABIX_DIR"

echo "Starting ABIX..."

docker compose -f docker/docker-compose.yml up -d 2>/dev/null || true

for svc in stt-service tts-service nlu-service; do
    port="${svc%%-*}"
    case "$svc" in
        stt-service) port=8001 ;;
        tts-service) port=8002 ;;
        nlu-service) port=8003 ;;
    esac
    for i in $(seq 1 30); do
        if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
done

echo "Services ready. Starting agent..."

ps aux | grep "agent.main" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null

nohup .venv/bin/python -m agent.main > /tmp/abix_agent.log 2>&1 &
AGENT_PID=$!

for i in $(seq 1 15); do
    if grep -q "UI client connected\|server listening" /tmp/abix_agent.log 2>/dev/null; then
        break
    fi
    sleep 1
done

echo "Agent ready (PID $AGENT_PID). Launching UI..."

cd frontend
npx electron --no-sandbox . &
UI_PID=$!

echo "ABIX running — agent PID $AGENT_PID, UI PID $UI_PID"
echo "Close the UI window to shut down everything."

wait $UI_PID 2>/dev/null

echo "UI closed. Shutting down agent..."
kill $AGENT_PID 2>/dev/null
sleep 2
