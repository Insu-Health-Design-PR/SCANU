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

cd "$ROOT_DIR/software"
exec "$CONDA_PREFIX/bin/python" -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
