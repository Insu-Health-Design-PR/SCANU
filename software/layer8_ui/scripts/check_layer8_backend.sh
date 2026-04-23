#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8087}"

check() {
  local path="$1"
  local url="${BACKEND_URL}${path}"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "$url" || true)"
  if [[ "$code" == "200" ]]; then
    echo "[ok] ${url} -> 200"
  else
    echo "[FAIL] ${url} -> ${code}"
    return 1
  fi
}

echo "[check] backend: ${BACKEND_URL}"
check "/api/health"
check "/api/status"
check "/api/visual/latest"
check "/api/alerts/recent?limit=10"
check "/api/layers/summary"

echo "[PASS] backend endpoints are reachable"

