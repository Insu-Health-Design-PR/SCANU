# Layer 8 Jetson E2E (60s)

This guide is for your Jetson path:

```bash
~/Desktop/SCANU-dev_adrian/software
```

## Quick Commands (copy/paste)

```bash
# Terminal A: start backend + frontend together
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

```bash
# Terminal B: validate live backend+frontend+cameras+sensors
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_live_jetson.sh
```

```bash
# Optional strict check: require point cloud data
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
REQUIRE_POINT_CLOUD=1 ./scripts/verify_layer8_live_jetson.sh
```

## 0) Install dependencies first

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m pip install -r layer8_ui/requirements.txt
cd layer8_ui/frontend
npm install
```

## 1) Start backend + frontend together (single command)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
chmod +x scripts/start_layer8_stack.sh
./scripts/start_layer8_stack.sh
```

Optional first run with frontend install:

```bash
INSTALL_FRONTEND_DEPS=1 ./scripts/start_layer8_stack.sh
```

## 2) Run API contract check (60s)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
chmod +x scripts/verify_layer8_e2e_60s.sh
./scripts/verify_layer8_e2e_60s.sh
```

Expected:

```text
[PASS] Layer 8 end-to-end compatibility checks passed
```

## 3) Run live hardware check (cameras + sensors)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
chmod +x scripts/verify_layer8_live_jetson.sh
./scripts/verify_layer8_live_jetson.sh
```

Optional strict point-cloud requirement:

```bash
REQUIRE_POINT_CLOUD=1 ./scripts/verify_layer8_live_jetson.sh
```

This script validates:

- frontend and backend are reachable
- CORS preflight works on `/api/ui/preferences`
- sensors become online (`sensor_online_count > 0`)
- `source_mode` becomes `live`
- RGB and Thermal frames are non-empty
- optional point-cloud presence

## 4) Open UI

Local Jetson browser:

```text
http://127.0.0.1:4173
```

From another device on LAN:

```bash
hostname -I
```

Then open:

```text
http://<JETSON_IP>:4173
```

## Notes

- Backend allows CORS for frontend development access.
- `start_layer8_stack.sh` no longer forces `VITE_LAYER8_API_BASE=127.0.0.1` by default.
  It lets frontend auto-resolve backend host, which is better for LAN access.
- If frontend fails because of Node/npm mismatch (`npm: command not found`, `dpkg` overwrite errors), use:

```text
software/layer8_ui/NODE20_JETSON_RECOVERY.md
```
