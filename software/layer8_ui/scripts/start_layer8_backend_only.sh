#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER8_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOFTWARE_DIR="$(cd "$LAYER8_DIR/.." && pwd)"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8088}"

LOG_DIR="$LAYER8_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.only.log"

mkdir -p "$LOG_DIR"

echo "[layer8-backend] Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
echo "[layer8-backend] Log: ${BACKEND_LOG}"

cd "$SOFTWARE_DIR"
python3 -m uvicorn layer8_ui.app:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" 2>&1 | tee "$BACKEND_LOG"
