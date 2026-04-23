#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8088}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:4173}"
DURATION_SEC="${DURATION_SEC:-60}"
INTERVAL_SEC="${INTERVAL_SEC:-5}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[FAIL] Missing required command: $1"
    exit 1
  }
}

need_cmd curl
need_cmd python3

echo "[check] backend : $BACKEND_URL"
echo "[check] frontend: $FRONTEND_URL"
echo "[check] duration: ${DURATION_SEC}s"

check_http_200() {
  local url="$1"
  local code
  code="$(curl -sS -o /tmp/layer8_resp.$$ -w "%{http_code}" "$url" || true)"
  if [[ "$code" != "200" ]]; then
    echo "[FAIL] $url -> HTTP $code"
    exit 1
  fi
  echo "[ok] $url -> 200"
}

check_http_200 "$FRONTEND_URL"
check_http_200 "$BACKEND_URL/api/status"
check_http_200 "$BACKEND_URL/api/health"
check_http_200 "$BACKEND_URL/api/alerts/recent?limit=10"
check_http_200 "$BACKEND_URL/api/visual/latest"
check_http_200 "$BACKEND_URL/api/ui/preferences"

python3 - "$BACKEND_URL" <<'PY'
import json
import sys
import urllib.request

base = sys.argv[1].rstrip("/")

def get_json(path):
    with urllib.request.urlopen(base + path, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))

status = get_json("/api/status")
health = get_json("/api/health")
visual = get_json("/api/visual/latest")
prefs = get_json("/api/ui/preferences")

required_status = {"state", "fused_score", "confidence", "health"}
required_health = {"healthy", "has_fault", "sensor_online_count"}
required_visual = {"timestamp_ms", "source_mode", "rgb_jpeg_b64", "thermal_jpeg_b64", "point_cloud", "presence"}
required_prefs = {"appliedLayout", "previewLayout", "focusView", "layoutStyle", "customModules"}

missing = []
for key in required_status:
    if key not in status:
        missing.append(f"/api/status missing {key}")
for key in required_health:
    if key not in health:
        missing.append(f"/api/health missing {key}")
for key in required_visual:
    if key not in visual:
        missing.append(f"/api/visual/latest missing {key}")
for key in required_prefs:
    if key not in prefs:
        missing.append(f"/api/ui/preferences missing {key}")

if missing:
    for m in missing:
        print("[FAIL]", m)
    raise SystemExit(1)

print("[ok] Contract keys validated")
PY

echo "[check] monitoring /api/visual/latest for ${DURATION_SEC}s..."
python3 - "$BACKEND_URL" "$DURATION_SEC" "$INTERVAL_SEC" <<'PY'
import json
import sys
import time
import urllib.request

base = sys.argv[1].rstrip("/")
duration = int(sys.argv[2])
interval = int(sys.argv[3])

def get_visual():
    with urllib.request.urlopen(base + "/api/visual/latest", timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))

start = time.time()
timestamps = []
while time.time() - start < duration:
    visual = get_visual()
    ts = visual.get("timestamp_ms")
    if isinstance(ts, (int, float)):
        timestamps.append(float(ts))
    time.sleep(interval)

if not timestamps:
    print("[FAIL] No timestamp_ms values observed in /api/visual/latest")
    raise SystemExit(1)

increases = sum(1 for i in range(1, len(timestamps)) if timestamps[i] > timestamps[i-1])
print(f"[ok] Observed {len(timestamps)} visual samples, increasing timestamps: {increases}")
PY

echo "[check] websocket /ws/events (optional)..."
python3 - "$BACKEND_URL" <<'PY'
import asyncio
import json
import sys

base = sys.argv[1].replace("http://", "ws://").replace("https://", "wss://").rstrip("/")
url = base + "/ws/events"

try:
    import websockets
except Exception:
    print("[warn] websockets package not installed; skipping ws/events check")
    raise SystemExit(0)

async def main():
    async with websockets.connect(url, open_timeout=5, close_timeout=2) as ws:
        seen = set()
        for _ in range(6):
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            evt = json.loads(raw)
            et = evt.get("event_type")
            if et:
                seen.add(et)
        need = {"status_update", "visual_update"}
        if not need.issubset(seen):
            print(f"[FAIL] ws/events missing expected event types. seen={sorted(seen)}")
            raise SystemExit(1)
        print(f"[ok] ws/events seen={sorted(seen)}")

asyncio.run(main())
PY

echo "[PASS] Layer 8 end-to-end compatibility checks passed"
