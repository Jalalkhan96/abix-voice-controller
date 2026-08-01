#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Local PortAudio lib (system one is missing; obtained without root via apt-get download)
export LD_LIBRARY_PATH="$ROOT/.libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo "==> Starting Docker services (STT/TTS/NLU)"
(cd docker && docker compose up -d)

echo "  waiting for services..."
for p in 8001 8002 8003; do
  for i in $(seq 1 30); do
    if curl -s --max-time 2 "localhost:$p/health" >/dev/null 2>&1; then
      echo "  :$p ready"; break
    fi
    sleep 2
  done
done

source .venv/bin/activate

echo "==> Backend API on :8010"
if curl -s --max-time 2 localhost:8010/health >/dev/null 2>&1; then
  echo "  already running"
else
  nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8010 \
    >/tmp/abix_backend.log 2>&1 &
  echo "  backend pid $!"
fi

echo "==> Agent (WebSocket :8765 + voice loop)"
if pgrep -f "agent.main" >/dev/null 2>&1; then
  echo "  already running"
else
  nohup python -m agent.main >/tmp/abix_agent.log 2>&1 &
  echo "  agent pid $!"
fi

echo "==> Electron frontend"
cd frontend
npm run build >/tmp/abix_frontend_build.log 2>&1 || true
exec ./node_modules/.bin/electron --no-sandbox .
