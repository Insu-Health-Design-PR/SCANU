#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8088}"
LAYER8_API_KEY="${LAYER8_API_KEY:-}"

check() {
  local path="$1"
  local auth_required="${2:-1}"
  local url="${BACKEND_URL}${path}"
  local code
  if [[ "$auth_required" == "1" && -n "$LAYER8_API_KEY" ]]; then
    code="$(curl -s -o /dev/null -w "%{http_code}" -H "X-Layer8-Api-Key: ${LAYER8_API_KEY}" "$url" || true)"
  else
    code="$(curl -s -o /dev/null -w "%{http_code}" "$url" || true)"
  fi
  if [[ "$code" == "200" ]]; then
    echo "[ok] ${url} -> 200"
  else
    echo "[FAIL] ${url} -> ${code}"
    return 1
  fi
}

echo "[check] backend: ${BACKEND_URL}"
check "/api/health" 0
check "/api/status"
check "/api/visual/latest"
check "/api/alerts/recent?limit=10"
check "/api/layers/summary"

echo "[PASS] backend endpoints are reachable"
