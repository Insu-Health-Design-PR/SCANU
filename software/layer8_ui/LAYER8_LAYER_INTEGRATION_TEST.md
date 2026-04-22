# Layer 8 Integration Test (Layers 1..8)

Use this test to validate, from terminal, that Layer 8 is collecting and exposing data from the full layer map.

Path on Jetson:

```bash
~/Desktop/SCANU-dev_adrian/software/layer8_ui
```

## 1) Start Layer 8 stack

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

## 2) Run integration test (contract + integration wiring)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_layers_integration.sh
```

Expected final line:

```text
[PASS] Layer integration with Layer 8 passed
```

## 3) Strict runtime mode (requires live hardware data)

Use this when you want to enforce that Layer 1 sensors are online and Layer 4 metrics are active.

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
STRICT_RUNTIME=1 ./scripts/verify_layer8_layers_integration.sh
```

In strict mode, test fails if:

- `layer1.sensor_online_count` never becomes `> 0`
- `layer4.metrics_available` never becomes `true`

## 4) Optional custom targets

```bash
BACKEND_URL="http://127.0.0.1:8087" \
FRONTEND_URL="http://127.0.0.1:4173" \
SAMPLES=12 \
INTERVAL_SEC=3 \
./scripts/verify_layer8_layers_integration.sh
```

## 5) Manual quick check

```bash
curl -s http://127.0.0.1:8080/api/layers/summary | jq
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
