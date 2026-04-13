# Layer 8 Test Commands

Use these commands to validate L6 -> L7 -> L8 end-to-end on Jetson.

## 1) Setup
```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn pyserial numpy websockets
```

## 2) Run stack in live mode (mmWave + IFX presence)
```bash
./software/layer8_ui/scripts/run_live_ifx.sh
```

Optional IFX UUID:
```bash
./software/layer8_ui/scripts/run_live_ifx.sh --ifx-uuid <YOUR_IFX_UUID>
```

Optional skip mmWave re-config:
```bash
./software/layer8_ui/scripts/run_live_ifx.sh --skip-mmwave-config
```

## 3) Check REST endpoints
```bash
curl http://127.0.0.1:8080/api/status
curl http://127.0.0.1:8080/api/health
curl 'http://127.0.0.1:8080/api/alerts/recent?limit=10'
```

## 4) Check WebSocket stream manually
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

## 5) Automated smoke test
```bash
python3 software/layer8_ui/scripts/smoke_layer8_stack.py --host 127.0.0.1 --port 8080
```

Expected:
```text
[PASS] Layer 8 smoke test completed
```
