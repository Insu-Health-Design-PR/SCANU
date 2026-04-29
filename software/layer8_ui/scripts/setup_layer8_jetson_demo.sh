#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER8_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOFTWARE_DIR="$(cd "$LAYER8_DIR/.." && pwd)"
FRONTEND_DIR="$LAYER8_DIR/frontend"
VENV_DIR="$SOFTWARE_DIR/.venv"

INSTALL_SYSTEM_DEPS="${INSTALL_SYSTEM_DEPS:-0}"
INSTALL_NODE_DEPS="${INSTALL_NODE_DEPS:-1}"
INSTALL_LAYER4_FULL="${INSTALL_LAYER4_FULL:-0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[setup] software dir: $SOFTWARE_DIR"
echo "[setup] layer8 dir  : $LAYER8_DIR"
echo "[setup] venv dir    : $VENV_DIR"

if [[ "$INSTALL_SYSTEM_DEPS" == "1" ]]; then
  echo "[setup] Installing system dependencies via apt..."
  sudo apt update
  sudo apt install -y \
    git \
    curl \
    ca-certificates \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    v4l-utils \
    ffmpeg \
    libgl1 \
    libglib2.0-0
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[setup] Creating Python virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [[ ! -x "$VENV_DIR/bin/pip" ]]; then
  echo "[setup] Virtual environment exists but pip/ensurepip is missing."
  echo "[setup] This usually means python venv packages are incomplete."
  echo "[setup] Fix with:"
  echo "  sudo apt update"
  echo "  sudo apt install -y python3-venv python3-pip"
  echo "  # if needed, install version-specific package too:"
  echo "  sudo apt install -y python3.8-venv || true"
  echo "  sudo apt install -y python3.10-venv || true"
  echo "  rm -rf \"$VENV_DIR\""
  echo "  \"$PYTHON_BIN\" -m venv \"$VENV_DIR\""
  echo "  source \"$VENV_DIR/bin/activate\""
  exit 2
fi

echo "[setup] Upgrading pip tooling..."
python3 -m pip install --upgrade pip setuptools wheel

echo "[setup] Installing Layer 8 and Layer 1 dependencies..."
python3 -m pip install -r "$SOFTWARE_DIR/layer8_ui/requirements.txt"
python3 -m pip install -r "$SOFTWARE_DIR/layer1_radar/requirements.txt"

echo "[setup] Checking torch / torchvision status..."
python3 - <<'PY'
try:
    import torch
    print("[setup] torch:", torch.__version__)
except Exception as exc:
    print("[setup] torch import failed:", exc)
try:
    import torchvision
    print("[setup] torchvision:", torchvision.__version__)
except Exception as exc:
    print("[setup] torchvision import failed:", exc)
PY

if [[ "$INSTALL_LAYER4_FULL" == "1" ]]; then
  echo "[setup] Installing full Layer 4 requirements (may replace Jetson torch wheels)..."
  python3 -m pip install -r "$SOFTWARE_DIR/layer4_inference/requirements.txt"
else
  echo "[setup] Installing Layer 4 safe subset (keeps existing torch/torchvision)..."
  python3 -m pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
fi

if [[ "$INSTALL_NODE_DEPS" == "1" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "[setup] npm not found. Install Node 20 first, then re-run."
    echo "[setup] Example:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "  sudo apt install -y nodejs"
    exit 2
  fi
  echo "[setup] Installing frontend npm dependencies..."
  (
    cd "$FRONTEND_DIR"
    npm install
  )
fi

echo "[setup] Hardware quick checks..."
if command -v v4l2-ctl >/dev/null 2>&1; then
  v4l2-ctl --list-devices || true
else
  echo "[setup] v4l2-ctl not found; skip camera listing."
fi
ls /dev/ttyUSB* 2>/dev/null || true
ls /dev/ttyACM* 2>/dev/null || true

echo "[setup] Completed successfully."
echo "[setup] Next step:"
echo "  cd \"$LAYER8_DIR\""
echo "  LAYER8_API_KEY=\"change-this-key\" ./scripts/run_layer8_jetson_vercel_demo.sh"
