#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER8_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOFTWARE_DIR="$(cd "$LAYER8_DIR/.." && pwd)"
FRONTEND_DIR="$LAYER8_DIR/frontend"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8088}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
INSTALL_FRONTEND_DEPS="${INSTALL_FRONTEND_DEPS:-0}"

LOG_DIR="$LAYER8_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.dev.log"
FRONTEND_LOG="$LOG_DIR/frontend.dev.log"

mkdir -p "$LOG_DIR"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "[layer8] Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "$SOFTWARE_DIR"
  python3 -m uvicorn layer8_ui.app:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

if [[ "$INSTALL_FRONTEND_DEPS" == "1" ]]; then
  echo "[layer8] Installing frontend dependencies..."
  (
    cd "$FRONTEND_DIR"
    npm install
  )
fi

echo "[layer8] Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd "$FRONTEND_DIR"
  if [[ -n "${VITE_LAYER8_API_BASE:-}" ]]; then
    export VITE_LAYER8_API_BASE
  fi
  if [[ -n "${VITE_LAYER8_WS_URL:-}" ]]; then
    export VITE_LAYER8_WS_URL
  fi
  if [[ -n "${VITE_LAYER8_API_KEY:-}" ]]; then
    export VITE_LAYER8_API_KEY
  fi
  npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort
) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

echo "[layer8] Backend PID:  ${BACKEND_PID}"
echo "[layer8] Frontend PID: ${FRONTEND_PID}"
echo "[layer8] Frontend URL: http://127.0.0.1:${FRONTEND_PORT}"
echo "[layer8] Backend URL:  http://127.0.0.1:${BACKEND_PORT}"
echo "[layer8] API/WS override:"
echo "  - VITE_LAYER8_API_BASE=${VITE_LAYER8_API_BASE:-<auto>}"
echo "  - VITE_LAYER8_WS_URL=${VITE_LAYER8_WS_URL:-<auto>}"
echo "  - VITE_LAYER8_API_KEY=${VITE_LAYER8_API_KEY:+<configured>}"
echo "[layer8] Camera override:"
echo "  - LAYER8_RGB_CAMERA_DEVICE=${LAYER8_RGB_CAMERA_DEVICE:-<settings/default>}"
echo "  - LAYER8_THERMAL_CAMERA_DEVICE=${LAYER8_THERMAL_CAMERA_DEVICE:-<settings/default>}"
echo "[layer8] Logs:"
echo "  - ${BACKEND_LOG}"
echo "  - ${FRONTEND_LOG}"
echo "[layer8] Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "[layer8] Backend stopped. Check log: ${BACKEND_LOG}"
    exit 1
  fi
  if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    echo "[layer8] Frontend stopped. Check log: ${FRONTEND_LOG}"
    exit 1
  fi
  sleep 2
done
