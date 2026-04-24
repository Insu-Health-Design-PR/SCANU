# Layer 8 Startup And Tests (Jetson)

Base path on Jetson:

```bash
~/Desktop/SCANU-dev_adrian/software/layer8_ui
```

## 1) Install dependencies

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m pip install -r layer8_ui/requirements.txt
cd layer8_ui/frontend
npm install
```

## 2) Start backend + frontend (single command)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

Defaults:
- backend: `http://127.0.0.1:8088`
- frontend: `http://127.0.0.1:4173`

## 3) Start backend only (debug mode)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_backend_only.sh
```

With API key protection enabled:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_only.sh
```

## 4) Quick backend check (health/status/routes)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/check_layer8_backend.sh
```

When `LAYER8_API_KEY` is enabled on the backend:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
LAYER8_API_KEY="change-this-key" ./scripts/check_layer8_backend.sh
```

## 5) Optional custom ports/URLs

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
BACKEND_PORT=8088 \
VITE_LAYER8_API_BASE="http://127.0.0.1:8088" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:8088/ws/events" \
./scripts/start_layer8_stack.sh
```

## 6) Run API contract test (60s)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_e2e_60s.sh
```

Expected:

```text
[PASS] Layer 8 end-to-end compatibility checks passed
```

## 7) Run live hardware test (Jetson)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_live_jetson.sh
```

Strict point-cloud check:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
REQUIRE_POINT_CLOUD=1 ./scripts/verify_layer8_live_jetson.sh
```

## 8) Run layer integration test (L1..L8)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_layers_integration.sh
```

Strict runtime:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
STRICT_RUNTIME=1 ./scripts/verify_layer8_layers_integration.sh
```

## 9) Open the UI

- Local Jetson: `http://127.0.0.1:4173`
- From LAN: `http://<JETSON_IP>:4173`

Get Jetson IP:

```bash
hostname -I
```
