#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/insu/Desktop/SCANU-dev_kpr-layer8"
CONDA_HOME="/home/insu/miniforge3"
CONDA_ENV="scanu-gpu"
OPENBLAS_DIR="$ROOT_DIR/.local-libs/openblas/extracted/usr/lib/aarch64-linux-gnu/openblas-pthread"

source "$CONDA_HOME/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

export PYTHONNOUSERSITE=1
export PYTHON="$CONDA_PREFIX/bin/python"
export THERMAL_PYTHON="$CONDA_HOME/envs/scanu-thermal/bin/python"
export LD_LIBRARY_PATH="$OPENBLAS_DIR:/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"

# Thermal/webcam/mmWave subprocess stdout — skip layer8_ui/logs/*.log to cut disk + CPU (see sensor_runner.py).
export LAYER8_SENSOR_LOG="${LAYER8_SENSOR_LOG:-0}"

cd "$ROOT_DIR/software"
# Default log level INFO so startup lines still print; WARNING hides them and looks like a hang.
echo "SCANU Layer 8 — starting uvicorn http://0.0.0.0:8088 (access-log off; UVICORN_LOG_LEVEL to change)" >&2
exec "$CONDA_PREFIX/bin/python" -m uvicorn layer8_ui.app:app \
  --host 0.0.0.0 \
  --port 8088 \
  --log-level "${UVICORN_LOG_LEVEL:-info}" \
  --no-access-log
