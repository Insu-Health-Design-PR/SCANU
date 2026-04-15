# Layer 8 Commands (Jetson / Dev)

## Jetson Path + Dependencies
If your Jetson workspace path is different from this Mac, use your local path:

```bash
cd /home/Desktop/SCANU-dev_adrian/software/layer8_ui
```

If your folder names are lowercase:

```bash
cd /home/desktop/scanu-dev_adrian/software/layer8_ui
```

Backend dependencies (Python):

```bash
cd /home/Desktop/SCANU-dev_adrian/software
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r layer8_ui/requirements.txt
pip install fastapi uvicorn websockets pyserial numpy
```

Frontend dependencies (Node):

```bash
cd /home/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm ci
```

Then run full live stack:

```bash
cd /home/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/run_jetson_full_stack.sh
```


## 0) Quick local stack (recommended)
Run backend + frontend together:
```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui
./scripts/run_local_stack.sh
```

Modes:
```bash
# default: simulate
BACKEND_MODE=simulate ./scripts/run_local_stack.sh

# API only backend (no simulated producer)
BACKEND_MODE=api ./scripts/run_local_stack.sh
```

Default URLs:
- Frontend: `http://127.0.0.1:4173`
- Backend: `http://127.0.0.1:8080`
- Health: `http://127.0.0.1:8080/api/health`

This command guide runs the new Layer 8 backend and validates L6->L7->L8 flow.

## 1) Environment
```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn pyserial numpy websockets
```

## 2) Run Layer 8 API only
```bash
PYTHONPATH=. python3 -m software.layer8_ui.backend.run_layer8 --host 0.0.0.0 --port 8080
```

## 3) Run integrated stack (simulate)
```bash
PYTHONPATH=. python3 -m software.layer8_ui.backend.run_layer8_stack \
  --mode simulate \
  --host 0.0.0.0 \
  --port 8080 \
  --radar-id radar_main \
  --interval-s 0.2 \
  --max-frames 0
```

## 4) Run integrated stack (live + IFX real)
Direct command:
```bash
PYTHONPATH=. python3 -m software.layer8_ui.backend.run_layer8_stack \
  --mode live \
  --host 0.0.0.0 \
  --port 8080 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/full_config.cfg \
  --mmwave on \
  --presence ifx \
  --ifx-uuid <YOUR_IFX_UUID_OPTIONAL> \
  --thermal off \
  --max-frames 0
```

Shortcut script (recommended):
```bash
./software/layer8_ui/scripts/run_live_ifx.sh
```

With custom IFX UUID:
```bash
./software/layer8_ui/scripts/run_live_ifx.sh --ifx-uuid <YOUR_IFX_UUID>
```

If you already configured radar and want to skip config:
```bash
./software/layer8_ui/scripts/run_live_ifx.sh --skip-mmwave-config
```

Notes:
- `--ifx-uuid` is optional; if omitted, provider tries default device.
- If multiple IFX devices are connected, pass UUID explicitly.

## 5) Validate REST endpoints
```bash
curl http://127.0.0.1:8080/api/status
curl http://127.0.0.1:8080/api/health
curl 'http://127.0.0.1:8080/api/alerts/recent?limit=10'
```

## 6) Validate WebSocket stream
```bash
python3 - <<'PY'
import asyncio
import websockets

async def main():
    uri = "ws://127.0.0.1:8080/ws/events"
    async with websockets.connect(uri) as ws:
        for _ in range(8):
            print(await ws.recv())

asyncio.run(main())
PY
```

Expected event types:
- `status_update`
- `alert_event`
- `heartbeat`
- `sensor_fault` (when health has fault)

## 7) End-to-end smoke test (automated)
With stack running, execute:
```bash
python3 software/layer8_ui/scripts/smoke_layer8_stack.py --host 127.0.0.1 --port 8080
```

Expected final line:
```text
[PASS] Layer 8 smoke test completed
```

## 8) Operational note
This runner keeps Layer 8 API contracts stable; when Layer 5 real output arrives, you only replace input source logic and keep API/WS unchanged.

## 9) Run stable test suite (timeouts)
```bash
./scripts/run_tests_layer8.sh
```
Optional:
```bash
RUN_E2E=1 ./scripts/run_tests_layer8.sh
```

## 10) Jetson Full Live Stack (frontend + backend + sensors)
Run everything in one command:
```bash
./scripts/run_jetson_full_stack.sh
```
Optional IFX UUID:
```bash
IFX_UUID=<YOUR_UUID> ./scripts/run_jetson_full_stack.sh
```
If thermal camera index differs:
```bash
THERMAL_DEVICE=1 RGB_DEVICE=0 ./scripts/run_jetson_full_stack.sh
```
If you need to skip radar config (already configured):
```bash
MMWAVE=on PRESENCE=ifx THERMAL=on RGB=on ./scripts/run_jetson_full_stack.sh --skip-mmwave-config
```

## 11) Auto-start on Jetson (systemd)
Install backend + frontend as services (boot persistence):

```bash
cd /home/Desktop/SCANU-dev_adrian/software/layer8_ui/scripts
./install_layer8_systemd.sh /home/Desktop/SCANU-dev_adrian <your-linux-user>
```

Check status:

```bash
sudo systemctl status layer8-backend layer8-frontend
```

Edit runtime options (ports, devices, IFX, etc.):

```bash
sudo nano /etc/default/layer8
sudo systemctl restart layer8-backend layer8-frontend
```

Disable auto-start if needed:

```bash
sudo systemctl disable --now layer8-backend layer8-frontend
```
