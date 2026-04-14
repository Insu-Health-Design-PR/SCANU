#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT_DIR"

: "${RADAR_ID:=radar_main}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8080}"
: "${CLI_PORT:=/dev/ttyUSB0}"
: "${DATA_PORT:=/dev/ttyUSB1}"
: "${CONFIG_PATH:=software/layer1_sensor_hub/testing/configs/full_config.cfg}"
: "${MAX_FRAMES:=0}"
: "${MMWAVE:=on}"
: "${PRESENCE:=ifx}"
: "${THERMAL:=off}"

EXTRA_ARGS=("$@")

exec PYTHONPATH=. python3 -m software.layer8_ui.backend.run_layer8_stack \
  --mode live \
  --host "$HOST" \
  --port "$PORT" \
  --radar-id "$RADAR_ID" \
  --cli-port "$CLI_PORT" \
  --data-port "$DATA_PORT" \
  --config "$CONFIG_PATH" \
  --max-frames "$MAX_FRAMES" \
  --mmwave "$MMWAVE" \
  --presence "$PRESENCE" \
  --thermal "$THERMAL" \
  "${EXTRA_ARGS[@]}"
