#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
LAYER8_DIR="$ROOT_DIR/software/layer8_ui"
FRONTEND_DIR="$LAYER8_DIR/frontend"

: "${HOST:=0.0.0.0}"
: "${BACKEND_PORT:=8080}"
: "${FRONTEND_PORT:=4173}"

# Live sensor defaults for Jetson
: "${RADAR_ID:=radar_main}"
: "${CLI_PORT:=/dev/ttyUSB0}"
: "${DATA_PORT:=/dev/ttyUSB1}"
: "${CONFIG_PATH:=software/layer1_sensor_hub/testing/configs/full_config.cfg}"
: "${MMWAVE:=on}"
: "${PRESENCE:=ifx}"
: "${IFX_UUID:=}"
: "${THERMAL:=on}"
: "${THERMAL_DEVICE:=0}"
: "${THERMAL_WIDTH:=640}"
: "${THERMAL_HEIGHT:=480}"
: "${THERMAL_FPS:=30}"
: "${RGB:=on}"
: "${RGB_DEVICE:=0}"
: "${RGB_WIDTH:=640}"
: "${RGB_HEIGHT:=480}"
: "${RGB_FPS:=30}"
: "${VISUAL:=on}"
: "${VISUAL_WIDTH:=640}"
: "${VISUAL_HEIGHT:=480}"
: "${MMWAVE_TIMEOUT_MS:=200}"
: "${INTERVAL_S:=0.2}"
: "${MAX_FRAMES:=0}"

BACKEND_LOG="/tmp/scanu_layer8_jetson_backend.log"
FRONTEND_LOG="/tmp/scanu_layer8_jetson_frontend.log"
HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/health"
FRONTEND_URL_LOCAL="http://127.0.0.1:${FRONTEND_PORT}"

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
  local retries="${3:-80}"
  local sleep_s="${4:-0.5}"

  for ((i=1; i<=retries; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_s"
  done

  echo "[layer8-jetson] ${name} probe failed after ${retries} retries"
  return 1
}

start_backend() {
  : > "$BACKEND_LOG"
  echo "[layer8-jetson] starting backend live on ${HOST}:${BACKEND_PORT}"

  EXTRA_ARGS=()
  if [[ -n "$IFX_UUID" ]]; then
    EXTRA_ARGS+=(--ifx-uuid "$IFX_UUID")
  fi

  PYTHONPATH="$ROOT_DIR" python3 -m software.layer8_ui.backend.run_layer8_stack \
    --mode live \
    --host "$HOST" \
    --port "$BACKEND_PORT" \
    --radar-id "$RADAR_ID" \
    --cli-port "$CLI_PORT" \
    --data-port "$DATA_PORT" \
    --config "$CONFIG_PATH" \
    --mmwave "$MMWAVE" \
    --presence "$PRESENCE" \
    --thermal "$THERMAL" \
    --thermal-device "$THERMAL_DEVICE" \
    --thermal-width "$THERMAL_WIDTH" \
    --thermal-height "$THERMAL_HEIGHT" \
    --thermal-fps "$THERMAL_FPS" \
    --rgb "$RGB" \
    --rgb-device "$RGB_DEVICE" \
    --rgb-width "$RGB_WIDTH" \
    --rgb-height "$RGB_HEIGHT" \
    --rgb-fps "$RGB_FPS" \
    --visual "$VISUAL" \
    --visual-width "$VISUAL_WIDTH" \
    --visual-height "$VISUAL_HEIGHT" \
    --mmwave-timeout-ms "$MMWAVE_TIMEOUT_MS" \
    --interval-s "$INTERVAL_S" \
    --max-frames "$MAX_FRAMES" \
    "${EXTRA_ARGS[@]}" \
    > "$BACKEND_LOG" 2>&1 &

  BACKEND_PID=$!

  if ! wait_for_url "$HEALTH_URL" "backend" 90 0.5; then
    echo "[layer8-jetson] backend log:"
    tail -n 160 "$BACKEND_LOG" || true
    exit 1
  fi
}

start_frontend() {
  : > "$FRONTEND_LOG"
  echo "[layer8-jetson] starting frontend on ${HOST}:${FRONTEND_PORT}"

  cd "$FRONTEND_DIR"
  VITE_LAYER8_API_BASE="http://127.0.0.1:${BACKEND_PORT}" \
  VITE_LAYER8_WS_URL="ws://127.0.0.1:${BACKEND_PORT}/ws/events" \
  node node_modules/vite/bin/vite.js --host "$HOST" --port "$FRONTEND_PORT" --strictPort > "$FRONTEND_LOG" 2>&1 &

  FRONTEND_PID=$!

  if ! wait_for_url "$FRONTEND_URL_LOCAL" "frontend" 80 0.5; then
    echo "[layer8-jetson] frontend log:"
    tail -n 160 "$FRONTEND_LOG" || true
    exit 1
  fi
}

get_lan_ip() {
  hostname -I 2>/dev/null | awk '{print $1}'
}

start_backend
start_frontend

LAN_IP="$(get_lan_ip || true)"

echo "[layer8-jetson] stack up"
echo "frontend (local): ${FRONTEND_URL_LOCAL}"
if [[ -n "${LAN_IP}" ]]; then
  echo "frontend (LAN)  : http://${LAN_IP}:${FRONTEND_PORT}"
  echo "backend  (LAN)  : http://${LAN_IP}:${BACKEND_PORT}"
fi
echo "backend (local) : http://127.0.0.1:${BACKEND_PORT}"
echo "health          : ${HEALTH_URL}"
echo "ws events       : ws://127.0.0.1:${BACKEND_PORT}/ws/events"
echo "[layer8-jetson] logs"
echo "  backend : ${BACKEND_LOG}"
echo "  frontend: ${FRONTEND_LOG}"
echo "[layer8-jetson] Press Ctrl+C to stop"

wait "$FRONTEND_PID"
