#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-8080}"

BASE="http://${HOST}:${PORT}"
WS="ws://${HOST}:${PORT}/ws/events"

echo "[smoke] checking REST endpoints on ${BASE}"
curl -fsS "${BASE}/api/health" >/dev/null
curl -fsS "${BASE}/api/status" >/dev/null
curl -fsS "${BASE}/api/visual/latest" >/dev/null
curl -fsS "${BASE}/api/ui/preferences" >/dev/null || true

echo "[smoke] running websocket smoke"
python3 /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui/scripts/smoke_layer8_stack.py --host "$HOST" --port "$PORT" --ws-count 4

echo "[smoke] PASS"
