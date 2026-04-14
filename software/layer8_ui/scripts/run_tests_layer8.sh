#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU"
LAYER8_DIR="$ROOT_DIR/software/layer8_ui"
FRONTEND_DIR="$LAYER8_DIR/frontend"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CREATE_VENV="${CREATE_VENV:-0}"
RUN_E2E="${RUN_E2E:-0}"
PYTEST_TIMEOUT_SEC="${PYTEST_TIMEOUT_SEC:-120}"
E2E_TIMEOUT_SEC="${E2E_TIMEOUT_SEC:-240}"

if [[ "$CREATE_VENV" == "1" ]]; then
  VENV_PATH="${VENV_PATH:-$ROOT_DIR/.venv}"
  if [[ ! -d "$VENV_PATH" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_PATH"
  fi
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
  PYTHON_BIN="python"
fi

run_with_timeout() {
  local timeout_sec="$1"
  local label="$2"
  shift 2

  echo "[layer8-tests] running: $label"

  "$PYTHON_BIN" - "$timeout_sec" "$label" "$@" <<'PY'
import subprocess
import sys

if len(sys.argv) < 4:
    raise SystemExit("usage: <timeout> <label> <cmd...>")

timeout = int(sys.argv[1])
label = sys.argv[2]
cmd = sys.argv[3:]

try:
    completed = subprocess.run(cmd, check=False, timeout=timeout)
except subprocess.TimeoutExpired:
    print(f"[layer8-tests] TIMEOUT ({timeout}s): {label}", file=sys.stderr)
    raise SystemExit(124)

raise SystemExit(completed.returncode)
PY
}

cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR"
export LAYER8_APP_SKIP_GLOBAL_BOOT=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "[layer8-tests] root: $ROOT_DIR"
echo "[layer8-tests] python: $PYTHON_BIN"

echo "[layer8-tests] phase 1: sanity imports"
run_with_timeout 30 "python import software" "$PYTHON_BIN" -c "import software; print('software ok')"
run_with_timeout 30 "python import pytest" "$PYTHON_BIN" -c "import pytest; print('pytest ok')"

echo "[layer8-tests] phase 2: backend tests"
run_with_timeout "$PYTEST_TIMEOUT_SEC" "pytest backend/testing" \
  "$PYTHON_BIN" -m pytest "$LAYER8_DIR/backend/testing" -q

if [[ "$RUN_E2E" == "1" ]]; then
  echo "[layer8-tests] phase 3: frontend e2e"
  cd "$FRONTEND_DIR"
  run_with_timeout "$E2E_TIMEOUT_SEC" "npm run test:e2e" npm run test:e2e
fi

echo "[layer8-tests] PASS"
