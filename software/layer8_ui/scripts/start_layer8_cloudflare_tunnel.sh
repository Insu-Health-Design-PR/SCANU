#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8088}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "[layer8-tunnel] cloudflared is not installed or not in PATH."
  echo "[layer8-tunnel] Install Cloudflare Tunnel first, then rerun this script."
  exit 2
fi

echo "[layer8-tunnel] Starting Cloudflare Tunnel to ${BACKEND_URL}"
echo "[layer8-tunnel] Copy the printed https://*.trycloudflare.com URL into Vercel:"
echo "[layer8-tunnel]   VITE_LAYER8_API_BASE=https://<printed-url>"
echo "[layer8-tunnel]   VITE_LAYER8_WS_URL=wss://<printed-url>/ws/events"

exec cloudflared tunnel --url "$BACKEND_URL"
