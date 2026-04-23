#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8088}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:4173}"
SAMPLES="${SAMPLES:-12}"
INTERVAL_SEC="${INTERVAL_SEC:-3}"
AUTO_START_SENSORS="${AUTO_START_SENSORS:-1}"
REQUIRE_POINT_CLOUD="${REQUIRE_POINT_CLOUD:-0}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[FAIL] Missing required command: $1"
    exit 1
  }
}

need_cmd curl
need_cmd python3

echo "[live-check] backend : $BACKEND_URL"
echo "[live-check] frontend: $FRONTEND_URL"
echo "[live-check] samples : $SAMPLES"
echo "[live-check] interval: ${INTERVAL_SEC}s"

check_http_200() {
  local url="$1"
  local code
  code="$(curl -sS -o /tmp/layer8_live_resp.$$ -w "%{http_code}" "$url" || true)"
  if [[ "$code" != "200" ]]; then
    echo "[FAIL] $url -> HTTP $code"
    exit 1
  fi
  echo "[ok] $url -> 200"
}

check_http_200 "$FRONTEND_URL"
check_http_200 "$BACKEND_URL/api/status"
check_http_200 "$BACKEND_URL/api/health"
check_http_200 "$BACKEND_URL/api/visual/latest"
check_http_200 "$BACKEND_URL/api/layers/summary"

echo "[live-check] CORS preflight /api/ui/preferences"
OPTIONS_CODE="$(curl -sS -o /tmp/layer8_live_cors.$$ -w "%{http_code}" -X OPTIONS \
  -H "Origin: http://127.0.0.1:4173" \
  -H "Access-Control-Request-Method: POST" \
  "$BACKEND_URL/api/ui/preferences" || true)"
if [[ "$OPTIONS_CODE" != "200" ]]; then
  echo "[FAIL] CORS preflight failed -> HTTP $OPTIONS_CODE"
  exit 1
fi
echo "[ok] CORS preflight -> 200"

if [[ "$AUTO_START_SENSORS" == "1" ]]; then
  echo "[live-check] starting sensors via /api/run_all..."
  curl -sS -X POST "$BACKEND_URL/api/run_all" -H "Content-Type: application/json" >/tmp/layer8_run_all.$$ || true
fi

python3 - "$BACKEND_URL" "$SAMPLES" "$INTERVAL_SEC" "$REQUIRE_POINT_CLOUD" <<'PY'
import base64
import json
import sys
import time
import urllib.request

base = sys.argv[1].rstrip("/")
samples = int(sys.argv[2])
interval = float(sys.argv[3])
require_pc = sys.argv[4] == "1"

def get_json(path):
    with urllib.request.urlopen(base + path, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))

rgb_seen = 0
thermal_seen = 0
pc_seen = 0
online_seen = 0
live_seen = 0
layers_integrated_seen = 0

for _ in range(samples):
    status = get_json("/api/status")
    visual = get_json("/api/visual/latest")
    layers = get_json("/api/layers/summary")
    online = int(((status.get("health") or {}).get("sensor_online_count")) or 0)
    if online > 0:
        online_seen += 1
    if visual.get("source_mode") == "live":
        live_seen += 1
    if isinstance(layers, dict):
        l = layers.get("layers") or {}
        l6 = l.get("layer6") or {}
        l7 = l.get("layer7") or {}
        if l6.get("integrated") is True and l7.get("integrated") is True:
            layers_integrated_seen += 1

    rgb = visual.get("rgb_jpeg_b64")
    thermal = visual.get("thermal_jpeg_b64")
    pc = visual.get("point_cloud") or []

    if isinstance(rgb, str) and rgb:
        try:
            if len(base64.b64decode(rgb)) > 1024:
                rgb_seen += 1
        except Exception:
            pass
    if isinstance(thermal, str) and thermal:
        try:
            if len(base64.b64decode(thermal)) > 1024:
                thermal_seen += 1
        except Exception:
            pass
    if isinstance(pc, list) and len(pc) > 0:
        pc_seen += 1

    time.sleep(interval)

failures = []
if online_seen == 0:
    failures.append("sensor_online_count never became > 0")
if live_seen == 0:
    failures.append("source_mode never became 'live'")
if rgb_seen == 0:
    failures.append("rgb_jpeg_b64 never had a non-empty frame")
if thermal_seen == 0:
    failures.append("thermal_jpeg_b64 never had a non-empty frame")
if require_pc and pc_seen == 0:
    failures.append("point_cloud stayed empty while REQUIRE_POINT_CLOUD=1")
if layers_integrated_seen == 0:
    failures.append("layer6/layer7 integration was not observed in /api/layers/summary")

if failures:
    for f in failures:
        print("[FAIL]", f)
    raise SystemExit(1)

print("[ok] online samples:", online_seen, "of", samples)
print("[ok] live samples:", live_seen, "of", samples)
print("[ok] rgb frames:", rgb_seen, "of", samples)
print("[ok] thermal frames:", thermal_seen, "of", samples)
print("[ok] point cloud non-empty:", pc_seen, "of", samples)
print("[ok] layer6/layer7 integrated samples:", layers_integrated_seen, "of", samples)
print("[PASS] Layer 8 live Jetson check passed")
PY
