#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU"
FRONTEND_DIR="$ROOT_DIR/software/layer8_ui/frontend"
BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
HOST="${HOST:-0.0.0.0}"
BACKEND_MODE="${BACKEND_MODE:-simulate}" # simulate | api
HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/health"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
BACKEND_LOG="/tmp/scanu_backend.log"
FRONTEND_LOG="/tmp/scanu_frontend.log"

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

wait_for_url() {
  local url="$1"
  local name="$2"
  local retries="${3:-40}"
  local sleep_s="${4:-0.5}"

  for ((i=1; i<=retries; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_s"
  done

  echo "[layer8] ${name} probe failed after ${retries} retries"
  return 1
}

start_backend() {
  : > "$BACKEND_LOG"
  echo "[layer8] starting backend (${BACKEND_MODE}) on ${HOST}:${BACKEND_PORT}"

  if [[ "$BACKEND_MODE" == "simulate" ]]; then
    PYTHONPATH="$ROOT_DIR" python3 -m software.layer8_ui.backend.run_layer8_stack \
      --mode simulate \
      --host "$HOST" \
      --port "$BACKEND_PORT" \
      --radar-id radar_main \
      --interval-s 0.2 \
      --max-frames 0 \
      --visual on \
      > "$BACKEND_LOG" 2>&1 &
  else
    PYTHONPATH="$ROOT_DIR" python3 -m software.layer8_ui.backend.run_layer8 \
      --host "$HOST" \
      --port "$BACKEND_PORT" \
      > "$BACKEND_LOG" 2>&1 &
  fi

  BACKEND_PID=$!

  if ! wait_for_url "$HEALTH_URL" "backend" 60 0.5; then
    echo "[layer8] backend log:"
    tail -n 120 "$BACKEND_LOG" || true
    exit 1
  fi
}

start_frontend() {
  : > "$FRONTEND_LOG"
  echo "[layer8] starting frontend on ${HOST}:${FRONTEND_PORT}"

  cd "$FRONTEND_DIR"
  VITE_LAYER8_API_BASE="http://127.0.0.1:${BACKEND_PORT}" \
  VITE_LAYER8_WS_URL="ws://127.0.0.1:${BACKEND_PORT}/ws/events" \
  node node_modules/vite/bin/vite.js --host "$HOST" --port "$FRONTEND_PORT" --strictPort > "$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID=$!

  if ! wait_for_url "$FRONTEND_URL" "frontend" 60 0.5; then
    echo "[layer8] frontend log:"
    tail -n 120 "$FRONTEND_LOG" || true
    exit 1
  fi
}

start_backend
start_frontend

echo "[layer8] stack up"
echo "frontend: ${FRONTEND_URL}"
echo "backend : http://127.0.0.1:${BACKEND_PORT}"
echo "health  : ${HEALTH_URL}"
echo "[layer8] logs"
echo "  backend : ${BACKEND_LOG}"
echo "  frontend: ${FRONTEND_LOG}"
echo "[layer8] press Ctrl+C to stop"

wait "$FRONTEND_PID"
