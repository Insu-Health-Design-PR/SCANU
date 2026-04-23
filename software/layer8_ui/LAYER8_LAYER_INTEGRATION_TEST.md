# Layer 8 Integration Test (Layers 1..8)

Use this test to validate, from terminal, that Layer 8 is collecting and exposing data from the full layer map.

Path on Jetson:

```bash
~/Desktop/SCANU-dev_adrian/software/layer8_ui
```

## 0) Frontend dependency check (fix `vite: not found`)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
npx vite --version
```

## 1) Start Layer 8 stack

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

Run backend on `8087`:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
BACKEND_PORT=8087 \
VITE_LAYER8_API_BASE="http://127.0.0.1:8087" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:8087/ws/events" \
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



4444444444

insu@insu-desktop:~$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
npx vite --version

added 148 packages, and audited 149 packages in 8s

26 packages are looking for funding
  run `npm fund` for details

2 moderate severity vulnerabilities

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
vite/5.4.21 linux-arm64 node-v20.20.2
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
npx vite --version

up to date, audited 149 packages in 38s

26 packages are looking for funding
  run `npm fund` for details

2 moderate severity vulnerabilities

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
vite/5.4.21 linux-arm64 node-v20.20.2
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
[layer8] Starting backend on 0.0.0.0:8080
[layer8] Starting frontend on 0.0.0.0:4173
[layer8] Backend PID:  72355
[layer8] Frontend PID: 72356
[layer8] Frontend URL: http://127.0.0.1:4173
[layer8] Backend URL:  http://127.0.0.1:8080
[layer8] API/WS override:
  - VITE_LAYER8_API_BASE=<auto>
  - VITE_LAYER8_WS_URL=<auto>
[layer8] Logs:
  - /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/backend.dev.log
  - /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/frontend.dev.log
[layer8] Press Ctrl+C to stop both services.
[layer8] Frontend stopped. Check log: /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/frontend.dev.log
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
BACKEND_PORT=8087 \
VITE_LAYER8_API_BASE="http://127.0.0.1:8087" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:8087/ws/events" \
./scripts/start_layer8_stack.sh
[layer8] Starting backend on 0.0.0.0:8087
[layer8] Starting frontend on 0.0.0.0:4173
[layer8] Backend PID:  72416
[layer8] Frontend PID: 72417
[layer8] Frontend URL: http://127.0.0.1:4173
[layer8] Backend URL:  http://127.0.0.1:8087
[layer8] API/WS override:
  - VITE_LAYER8_API_BASE=http://127.0.0.1:8087
  - VITE_LAYER8_WS_URL=ws://127.0.0.1:8087/ws/events
[layer8] Logs:
  - /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/backend.dev.log
  - /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/frontend.dev.log
[layer8] Press Ctrl+C to stop both services.
[layer8] Frontend stopped. Check log: /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/frontend.dev.log
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_layers_integration.sh
[layers] backend : http://127.0.0.1:8080
[layers] frontend: http://127.0.0.1:4173
[layers] samples : 10
[layers] interval: 2s
[layers] strict  : 0
[ok] http://127.0.0.1:4173 -> 200
[ok] http://127.0.0.1:8080/api/status -> 200
[ok] http://127.0.0.1:8080/api/alerts/recent?limit=10 -> 200
[FAIL] http://127.0.0.1:8080/api/layers/summary -> HTTP 404
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
STRICT_RUNTIME=1 ./scripts/verify_layer8_layers_integration.sh
[layers] backend : http://127.0.0.1:8080
[layers] frontend: http://127.0.0.1:4173
[layers] samples : 10
[layers] interval: 2s
[layers] strict  : 1
[ok] http://127.0.0.1:4173 -> 200
[ok] http://127.0.0.1:8080/api/status -> 200
[ok] http://127.0.0.1:8080/api/alerts/recent?limit=10 -> 200
[FAIL] http://127.0.0.1:8080/api/layers/summary -> HTTP 404
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ 








