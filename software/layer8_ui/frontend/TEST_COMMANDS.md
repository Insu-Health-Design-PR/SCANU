# Layer 8 Frontend Test Commands

## 1) Start backend stack (simulate)
```bash
cd /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU
PYTHONPATH=. python3 -m software.layer8_ui.backend.run_layer8_stack \
  --mode simulate \
  --host 0.0.0.0 \
  --port 8080 \
  --radar-id radar_main \
  --interval-s 0.2 \
  --max-frames 0
```

## 2) Start frontend
```bash
cd /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:
- `http://127.0.0.1:5173/dashboard`
- `http://127.0.0.1:5173/control`
- `http://127.0.0.1:5173/events`

## 3) Validate backend contracts quickly
```bash
curl http://127.0.0.1:8080/api/status
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/sensors/status
curl 'http://127.0.0.1:8080/api/alerts/recent?limit=10'
```

## 4) Control API checks
```bash
curl -X POST http://127.0.0.1:8080/api/control/reset-soft \
  -H 'content-type: application/json' \
  -d '{"radar_id":"radar_main"}'

curl -X POST http://127.0.0.1:8080/api/control/reconfig \
  -H 'content-type: application/json' \
  -d '{"radar_id":"radar_main","config_path":"software/layer1_sensor_hub/testing/configs/full_config.cfg"}'
```

Destructive actions (manual confirm required by policy/UI):
```bash
curl -X POST http://127.0.0.1:8080/api/control/kill-holders \
  -H 'content-type: application/json' \
  -d '{"radar_id":"radar_main","force":true,"manual_confirm":true}'

curl -X POST http://127.0.0.1:8080/api/control/usb-reset \
  -H 'content-type: application/json' \
  -d '{"radar_id":"radar_main","manual_confirm":true}'
```

## 5) Frontend local quality checks
```bash
cd /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer8_ui/frontend
npm run build
npm run test -- --run
```
