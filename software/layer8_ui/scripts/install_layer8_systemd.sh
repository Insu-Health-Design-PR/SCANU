#!/usr/bin/env bash
set -euo pipefail

ROOT_DEFAULT="/home/Desktop/SCANU-dev_adrian"
ROOT_DIR="${1:-$ROOT_DEFAULT}"
SERVICE_USER="${2:-$USER}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TPL_DIR="$SCRIPT_DIR/systemd"

if [[ ! -d "$ROOT_DIR/software/layer8_ui" ]]; then
  echo "[layer8-systemd] error: '$ROOT_DIR/software/layer8_ui' not found"
  echo "usage: $0 <repo-root> <linux-user>"
  exit 1
fi

BACKEND_TMP="$(mktemp)"
FRONTEND_TMP="$(mktemp)"
trap 'rm -f "$BACKEND_TMP" "$FRONTEND_TMP"' EXIT

sed -e "s|__ROOT__|$ROOT_DIR|g" -e "s|__USER__|$SERVICE_USER|g" "$TPL_DIR/layer8-backend.service.tpl" > "$BACKEND_TMP"
sed -e "s|__ROOT__|$ROOT_DIR|g" -e "s|__USER__|$SERVICE_USER|g" "$TPL_DIR/layer8-frontend.service.tpl" > "$FRONTEND_TMP"

echo "[layer8-systemd] installing services for user '$SERVICE_USER' and root '$ROOT_DIR'"
sudo cp "$BACKEND_TMP" /etc/systemd/system/layer8-backend.service
sudo cp "$FRONTEND_TMP" /etc/systemd/system/layer8-frontend.service

if [[ ! -f /etc/default/layer8 ]]; then
  echo "[layer8-systemd] creating /etc/default/layer8 (editable config)"
  sudo tee /etc/default/layer8 >/dev/null <<CFG
# Layer8 runtime overrides (optional)
# LAYER8_HOST=0.0.0.0
# LAYER8_BACKEND_PORT=8080
# LAYER8_FRONTEND_PORT=4173
# LAYER8_CLI_PORT=/dev/ttyUSB0
# LAYER8_DATA_PORT=/dev/ttyUSB1
# LAYER8_PRESENCE=ifx
# LAYER8_IFX_UUID=
# LAYER8_THERMAL_DEVICE=0
# LAYER8_RGB_DEVICE=0
CFG
fi

sudo systemctl daemon-reload
sudo systemctl enable --now layer8-backend.service layer8-frontend.service

echo "[layer8-systemd] done"
echo "[layer8-systemd] backend : http://127.0.0.1:${LAYER8_BACKEND_PORT:-8080}"
echo "[layer8-systemd] frontend: http://127.0.0.1:${LAYER8_FRONTEND_PORT:-4173}"
echo "[layer8-systemd] status  : sudo systemctl status layer8-backend layer8-frontend"
