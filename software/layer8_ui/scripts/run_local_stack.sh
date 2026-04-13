#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU"
FRONTEND_DIR="$ROOT_DIR/software/layer8_ui/frontend"
BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
HOST="${HOST:-0.0.0.0}"

cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "[layer8] starting backend on ${HOST}:${BACKEND_PORT}"
PYTHONPATH="$ROOT_DIR" python3 -m uvicorn software.layer8_ui.app:app --host "$HOST" --port "$BACKEND_PORT" > /tmp/scanu_backend.log 2>&1 &
BACKEND_PID=$!

sleep 2
if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null; then
  echo "[layer8] backend health check failed"
  echo "[layer8] backend log:"
  tail -n 80 /tmp/scanu_backend.log || true
  exit 1
fi

echo "[layer8] starting frontend on ${HOST}:${FRONTEND_PORT}"
cd "$FRONTEND_DIR"
VITE_LAYER8_API_BASE="http://127.0.0.1:${BACKEND_PORT}" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:${BACKEND_PORT}/ws/events" \
node node_modules/vite/bin/vite.js --host "$HOST" --port "$FRONTEND_PORT" --strictPort > /tmp/scanu_frontend.log 2>&1 &
FRONTEND_PID=$!

sleep 2
if ! curl -fsS "http://127.0.0.1:${FRONTEND_PORT}" >/dev/null; then
  echo "[layer8] frontend probe failed"
  echo "[layer8] frontend log:"
  tail -n 80 /tmp/scanu_frontend.log || true
  exit 1
fi

echo "[layer8] stack up"
echo "frontend: http://127.0.0.1:${FRONTEND_PORT}"
echo "backend : http://127.0.0.1:${BACKEND_PORT}"

echo "[layer8] press Ctrl+C to stop"
wait "$FRONTEND_PID"
