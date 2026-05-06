#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER8_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOFTWARE_DIR="$(cd "$LAYER8_DIR/.." && pwd)"
VENV_DIR="$SOFTWARE_DIR/.venv"
LOG_DIR="$LAYER8_DIR/logs"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8088}"
INSTALL_SYSTEM_DEPS="${INSTALL_SYSTEM_DEPS:-0}"
INSTALL_LAYER4_FULL="${INSTALL_LAYER4_FULL:-0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<'EOF'
Usage: ./scripts/layer8.sh <command>

Commands:
  setup     Create/update software/.venv and install Python dependencies
  start     Start Layer 8 backend + static dashboard
  check     Check /api/health, /api/status, and /api/visual/latest
  run-all   Start all configured sensors through the API
  stop-all  Stop all configured sensors through the API

Environment:
  INSTALL_SYSTEM_DEPS=1   Install apt packages during setup
  INSTALL_LAYER4_FULL=1   Install full layer4_inference/requirements.txt
  BACKEND_HOST=0.0.0.0    Backend bind host
  BACKEND_PORT=8088       Backend port
  LAYER8_API_KEY=...      Optional API key for protected endpoints
EOF
}

activate_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "[layer8] Missing venv at: $VENV_DIR"
    echo "[layer8] Run: ./scripts/layer8.sh setup"
    exit 2
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

auth_args() {
  if [[ -n "${LAYER8_API_KEY:-}" ]]; then
    printf '%s\n' -H "X-Layer8-Api-Key: ${LAYER8_API_KEY}"
  fi
}

setup_cmd() {
  echo "[setup] software dir: $SOFTWARE_DIR"
  echo "[setup] layer8 dir  : $LAYER8_DIR"
  echo "[setup] venv dir    : $VENV_DIR"

  if [[ "$INSTALL_SYSTEM_DEPS" == "1" ]]; then
    sudo apt update
    sudo apt install -y \
      git curl ca-certificates python3-pip python3-venv python3-dev \
      build-essential v4l-utils ffmpeg libgl1 libglib2.0-0
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  activate_venv

  if [[ ! -x "$VENV_DIR/bin/pip" ]]; then
    echo "[setup] pip/ensurepip is missing in the virtual environment."
    echo "[setup] Install python3-venv/python3-pip, remove $VENV_DIR, and retry."
    exit 2
  fi

  python3 -m pip install --upgrade pip setuptools wheel
  python3 -m pip install -r "$SOFTWARE_DIR/layer8_ui/requirements.txt"
  python3 -m pip install -r "$SOFTWARE_DIR/layer1_radar/requirements.txt"

  if [[ "$INSTALL_LAYER4_FULL" == "1" ]]; then
    python3 -m pip install -r "$SOFTWARE_DIR/layer4_inference/requirements.txt"
  else
    python3 -m pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
  fi

  echo "[setup] Hardware quick checks:"
  v4l2-ctl --list-devices || true
  ls /dev/ttyUSB* 2>/dev/null || true
  ls /dev/ttyACM* 2>/dev/null || true
  echo "[setup] Done."
}

start_cmd() {
  activate_venv
  mkdir -p "$LOG_DIR"
  echo "[layer8] Starting backend/UI on ${BACKEND_HOST}:${BACKEND_PORT}"
  echo "[layer8] Open: http://127.0.0.1:${BACKEND_PORT}"
  echo "[layer8] Log: $LOG_DIR/backend.log"
  cd "$SOFTWARE_DIR"
  python3 -m uvicorn layer8_ui.app:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
    2>&1 | tee "$LOG_DIR/backend.log"
}

check_cmd() {
  local base="http://127.0.0.1:${BACKEND_PORT}"
  curl -fsS "$base/api/health"
  echo
  curl -fsS $(auth_args) "$base/api/status"
  echo
  curl -fsS $(auth_args) "$base/api/visual/latest" >/dev/null
  echo "[check] OK"
}

post_cmd() {
  local endpoint="$1"
  curl -fsS -X POST $(auth_args) "http://127.0.0.1:${BACKEND_PORT}${endpoint}"
  echo
}

cmd="${1:-}"
case "$cmd" in
  setup) setup_cmd ;;
  start) start_cmd ;;
  check) check_cmd ;;
  run-all) post_cmd "/api/run_all" ;;
  stop-all) post_cmd "/api/stop_all" ;;
  -h|--help|help|"") usage ;;
  *)
    echo "[layer8] Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac
