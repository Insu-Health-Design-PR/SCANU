#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON_SCRIPT="$ROOT_DIR/software/layer2_signal_processing/examples/run_sensor_layer1_layer2.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"

print_shell_help() {
  cat <<EOF
Usage:
  ./run_sensor_layer1_layer2.sh [runner args]

Launcher options:
  --shell-help   Show this launcher help and exit
  --check        Also list visible serial ports before delegating to Python

Environment:
  PYTHON_BIN     Override Python interpreter (default: python3)

Examples:
  ./run_sensor_layer1_layer2.sh --check
  ./run_sensor_layer1_layer2.sh --frames 10
  PYTHON_BIN=python3 ./run_sensor_layer1_layer2.sh --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --full
EOF
}

for arg in "$@"; do
  if [[ "$arg" == "--shell-help" ]]; then
    print_shell_help
    exit 0
  fi
done

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
  echo "Launcher error: Python runner not found at:" >&2
  echo "  $PYTHON_SCRIPT" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Launcher error: Python interpreter '$PYTHON_BIN' was not found in PATH." >&2
  exit 1
fi

cd "$ROOT_DIR"

echo "Repo root: $ROOT_DIR"
echo "Python: $("$PYTHON_BIN" --version 2>&1)"

for arg in "$@"; do
  if [[ "$arg" == "--check" ]]; then
    echo "Visible serial ports:"
    if ! ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null; then
      echo "(none found)"
    fi
    break
  fi
done

exec "$PYTHON_BIN" "$PYTHON_SCRIPT" "$@"
