# Layer 8 Commands (Jetson / Dev)

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
PYTHONPATH=. python3 -m software.layer8_ui.run_layer8 --host 0.0.0.0 --port 8080
```

## 3) Run integrated stack (simulate)
```bash
PYTHONPATH=. python3 -m software.layer8_ui.run_layer8_stack \
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
PYTHONPATH=. python3 -m software.layer8_ui.run_layer8_stack \
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
