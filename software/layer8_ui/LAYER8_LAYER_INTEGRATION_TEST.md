# Layer 8 Integration Test (Layers 1..8)

Use this test to validate, from terminal, that Layer 8 is collecting and exposing data from the full layer map.

Path on Jetson:

```bash
~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui
```

## 0) Frontend dependency check (fix `vite: not found`)

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui/frontend
npm install
npx vite --version
```

## 1) Start Layer 8 stack (default backend port 8087)

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui
./scripts/start_layer8_stack.sh
```

## 2) Optional custom port/API overrides

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui
BACKEND_PORT=8087 \
VITE_LAYER8_API_BASE="http://127.0.0.1:8087" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:8087/ws/events" \
./scripts/start_layer8_stack.sh
```

## 3) Run integration test (contract + integration wiring)

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui
./scripts/verify_layer8_layers_integration.sh
```

Expected final line:

```text
[PASS] Layer integration with Layer 8 passed
```

## 4) Strict runtime mode (requires live hardware data)

Use this when you want to enforce that Layer 1 sensors are online and Layer 4 metrics are active.

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui
STRICT_RUNTIME=1 ./scripts/verify_layer8_layers_integration.sh
```

In strict mode, test fails if:

- `layer1.sensor_online_count` never becomes `> 0`
- `layer4.metrics_available` never becomes `true`

## 5) Optional custom test targets

```bash
BACKEND_URL="http://127.0.0.1:8087" \
FRONTEND_URL="http://127.0.0.1:4173" \
SAMPLES=12 \
INTERVAL_SEC=3 \
./scripts/verify_layer8_layers_integration.sh
```

## 6) Manual quick checks

```bash
curl -s http://127.0.0.1:8087/api/layers/summary | jq
curl -s http://127.0.0.1:8087/api/status | jq
```

You should see layer keys:

- `layer1`
- `layer2`
- `layer3`
- `layer4`
- `layer5`
- `layer6`
- `layer7`
- `layer8`
