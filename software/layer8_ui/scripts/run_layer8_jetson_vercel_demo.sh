#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER8_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOFTWARE_DIR="$(cd "$LAYER8_DIR/.." && pwd)"
VENV_DIR="$SOFTWARE_DIR/.venv"
LOG_DIR="$LAYER8_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.vercel.demo.log"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8088}"
AUTO_START_SENSORS="${AUTO_START_SENSORS:-1}"
RUN_PUBLIC_CHECKS="${RUN_PUBLIC_CHECKS:-1}"

if [[ -z "${LAYER8_API_KEY:-}" ]]; then
  echo "[run] Missing LAYER8_API_KEY."
  echo "[run] Example:"
  echo "  LAYER8_API_KEY=\"change-this-key\" ./scripts/run_layer8_jetson_vercel_demo.sh"
  exit 2
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[run] Missing virtual env at: $VENV_DIR"
  echo "[run] Run setup first:"
  echo "  ./scripts/setup_layer8_jetson_demo.sh"
  exit 2
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "[run] cloudflared not found in PATH."
  echo "[run] Install Cloudflare Tunnel and retry."
  exit 2
fi

mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[run] Starting Layer 8 backend for Vercel..."
(
  cd "$LAYER8_DIR"
  BACKEND_HOST="$BACKEND_HOST" BACKEND_PORT="$BACKEND_PORT" \
    LAYER8_API_KEY="$LAYER8_API_KEY" ./scripts/start_layer8_backend_for_vercel.sh
) >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cleanup() {
  if kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "[run] Waiting backend health..."
for _ in $(seq 1 30); do
  code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${BACKEND_PORT}/api/health" || true)"
  if [[ "$code" == "200" ]]; then
    break
  fi
  sleep 1
done

if [[ "${code:-000}" != "200" ]]; then
  echo "[run] Backend did not become healthy. Check log: $BACKEND_LOG"
  exit 1
fi

echo "[run] Running local authenticated checks..."
(
  cd "$LAYER8_DIR"
  BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}" LAYER8_API_KEY="$LAYER8_API_KEY" \
    ./scripts/check_layer8_backend.sh
)

if [[ "$AUTO_START_SENSORS" == "1" ]]; then
  echo "[run] Starting sensors via /api/run_all..."
  curl -sS -X POST -H "X-Layer8-Api-Key: ${LAYER8_API_KEY}" \
    "http://127.0.0.1:${BACKEND_PORT}/api/run_all" >/dev/null || true
fi

echo "[run] Starting Cloudflare Tunnel..."
echo "[run] After URL appears, copy it and set these vars in Vercel:"
echo "[run]   VITE_LAYER8_API_BASE=https://<url>"
echo "[run]   VITE_LAYER8_WS_URL=wss://<url>/ws/events"
echo "[run]   VITE_LAYER8_API_KEY=<same-key>"
echo "[run] Backend log: $BACKEND_LOG"

if [[ "$RUN_PUBLIC_CHECKS" == "1" ]]; then
  echo "[run] Tip: after copying URL, run in another terminal:"
  echo "  BACKEND_URL=\"https://<url>\" LAYER8_API_KEY=\"${LAYER8_API_KEY}\" ./scripts/check_layer8_backend.sh"
fi

(
  cd "$LAYER8_DIR"
  BACKEND_PORT="$BACKEND_PORT" ./scripts/start_layer8_cloudflare_tunnel.sh
)
