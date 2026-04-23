#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8088}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:4173}"
SAMPLES="${SAMPLES:-10}"
INTERVAL_SEC="${INTERVAL_SEC:-2}"
AUTO_START_SENSORS="${AUTO_START_SENSORS:-1}"
STRICT_RUNTIME="${STRICT_RUNTIME:-0}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[FAIL] Missing required command: $1"
    exit 1
  }
}

need_cmd curl
need_cmd python3

echo "[layers] backend : $BACKEND_URL"
echo "[layers] frontend: $FRONTEND_URL"
echo "[layers] samples : $SAMPLES"
echo "[layers] interval: ${INTERVAL_SEC}s"
echo "[layers] strict  : $STRICT_RUNTIME"

check_http_200() {
  local url="$1"
  local code
  code="$(curl -sS -o /tmp/layer8_layers_resp.$$ -w "%{http_code}" "$url" || true)"
  if [[ "$code" != "200" ]]; then
    echo "[FAIL] $url -> HTTP $code"
    exit 1
  fi
  echo "[ok] $url -> 200"
}

check_http_200 "$FRONTEND_URL"
check_http_200 "$BACKEND_URL/api/status"
check_http_200 "$BACKEND_URL/api/alerts/recent?limit=10"
check_http_200 "$BACKEND_URL/api/layers/summary"

if [[ "$AUTO_START_SENSORS" == "1" ]]; then
  echo "[layers] starting sensors via /api/run_all..."
  curl -sS -X POST "$BACKEND_URL/api/run_all" -H "Content-Type: application/json" >/tmp/layer8_layers_run_all.$$ || true
fi

python3 - "$BACKEND_URL" "$SAMPLES" "$INTERVAL_SEC" "$STRICT_RUNTIME" <<'PY'
import json
import sys
import time
import urllib.request

base = sys.argv[1].rstrip('/')
samples = int(sys.argv[2])
interval = float(sys.argv[3])
strict = sys.argv[4] == '1'

def get_json(path):
    with urllib.request.urlopen(base + path, timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))

required_layers = ['layer1','layer2','layer3','layer4','layer5','layer6','layer7','layer8']
layer_key_hits = {k: 0 for k in required_layers}
layer6_integrated_hits = 0
layer7_integrated_hits = 0
layer1_online_hits = 0
layer4_metrics_hits = 0

for _ in range(samples):
    summary = get_json('/api/layers/summary')
    layers = summary.get('layers') or {}

    for key in required_layers:
        if key in layers:
            layer_key_hits[key] += 1

    l1 = layers.get('layer1') or {}
    l4 = layers.get('layer4') or {}
    l6 = layers.get('layer6') or {}
    l7 = layers.get('layer7') or {}

    if int(l1.get('sensor_online_count') or 0) > 0:
        layer1_online_hits += 1
    if bool(l4.get('metrics_available')):
        layer4_metrics_hits += 1
    if bool(l6.get('integrated')):
        layer6_integrated_hits += 1
    if bool(l7.get('integrated')):
        layer7_integrated_hits += 1

    time.sleep(interval)

failures = []
for key, hits in layer_key_hits.items():
    if hits == 0:
        failures.append(f"/api/layers/summary never exposed {key}")

if layer6_integrated_hits == 0:
    failures.append('layer6.integrated was never true')
if layer7_integrated_hits == 0:
    failures.append('layer7.integrated was never true')

if strict:
    if layer1_online_hits == 0:
        failures.append('STRICT_RUNTIME=1 and layer1 sensor_online_count never became > 0')
    if layer4_metrics_hits == 0:
        failures.append('STRICT_RUNTIME=1 and layer4 metrics_available never became true')

if failures:
    for f in failures:
        print('[FAIL]', f)
    raise SystemExit(1)

print('[ok] Layer summary keys present for all layers 1..8')
print('[ok] layer6 integrated samples:', layer6_integrated_hits, 'of', samples)
print('[ok] layer7 integrated samples:', layer7_integrated_hits, 'of', samples)
print('[ok] layer1 online samples:', layer1_online_hits, 'of', samples)
print('[ok] layer4 metrics samples:', layer4_metrics_hits, 'of', samples)
print('[PASS] Layer integration with Layer 8 passed')
PY
