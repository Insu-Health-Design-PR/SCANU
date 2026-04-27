#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${LAYER8_API_KEY:-}" ]]; then
  echo "[layer8-vercel] Missing LAYER8_API_KEY."
  echo "[layer8-vercel] Example:"
  echo "  LAYER8_API_KEY=\"change-this-key\" ./scripts/start_layer8_backend_for_vercel.sh"
  exit 2
fi

export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-8088}"
export LAYER8_CORS_ORIGINS="${LAYER8_CORS_ORIGINS:-https://scanu-ui.vercel.app}"

echo "[layer8-vercel] Backend host: ${BACKEND_HOST}"
echo "[layer8-vercel] Backend port: ${BACKEND_PORT}"
echo "[layer8-vercel] CORS origins: ${LAYER8_CORS_ORIGINS}"
echo "[layer8-vercel] API key: configured"

exec "$SCRIPT_DIR/start_layer8_backend_only.sh"
