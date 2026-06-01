# Adrian Phase 2 Runbook

This runbook covers Adrian's mmWave + UI responsibilities for Phase 2.

## Flow

```text
mmWave data in -> normalized objects -> top-down preview -> camera overlay -> UI device/status/alerts
```

## 1. Run mmWave UART/TLV Capture

From the `software/` directory:

```bash
python3 -m layer1_sensor_hub.examples.live_capture \
  --mmwave-only \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config layer1_sensor_hub/examples/configs/stable_tracking_indoor2_low_uart.cfg \
  --frames 300 \
  --output layer8_ui/artifacts/mmwave_frames.json \
  --live-frame layer8_ui/artifacts/live_mmwave.jpg \
  --video layer8_ui/artifacts/mmwave_live.mp4
```

If the hardware is not connected, keep using the existing sample JSON in
`layer8_ui/artifacts/mmwave_frames.json`.

## 2. Normalize Existing mmWave JSON

```bash
python3 -m layer1_sensor_hub.mmwave.normalize_mmwave_json \
  --input layer8_ui/artifacts/mmwave_frames.json \
  --output layer8_ui/artifacts/mmwave_frames.normalized.json \
  --preview layer8_ui/artifacts/live_mmwave.jpg
```

The normalized contract is:

```json
{
  "frame_id": 1,
  "timestamp_ms": 0,
  "radar_id": "radar_main",
  "objects": [
    {
      "x": 0.0,
      "y": 1.0,
      "z": 0.0,
      "range_m": 1.0,
      "velocity_mps": 0.0,
      "snr": 10.0,
      "confidence": 0.3
    }
  ]
}
```

## 3. Start Layer 8 Dashboard

Build the React UI first:

```bash
cd layer8_ui/frontend
npm install
npm run build
cd ..
```

Or use the Layer 8 helper:

```bash
./scripts/layer8.sh frontend
```

Then start the backend. FastAPI serves the React build from
`layer8_ui/frontend/dist` automatically.

```bash
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Open:

```text
http://127.0.0.1:8088
```

The legacy static HTML remains as fallback only when `frontend/dist/index.html`
does not exist.

## 4. New API Checks

```bash
curl http://127.0.0.1:8088/api/devices
curl http://127.0.0.1:8088/api/mmwave/latest
curl http://127.0.0.1:8088/api/mmwave/frames
curl http://127.0.0.1:8088/api/mmwave/camera-overlay
curl -X POST http://127.0.0.1:8088/api/mmwave/preview/regenerate
curl http://127.0.0.1:8088/api/operator/state
```

## 5. Camera Overlay Calibration

Edit these mmWave settings from the dashboard config panel:

```text
projection_width
projection_height
projection_x_scale_px_per_m
projection_y_scale_px_per_m
projection_x_offset_px
projection_y_offset_px
projection_rotation_deg
projection_max_range_m
```

Use the webcam preview and move one person through known positions. Adjust scale,
offset, and rotation until radar dots match the camera view.

## 6. DCA1000 Raw ADC Path

## 6. Operator Modes And Tracking UI

The React UI exposes three operator modes:

```text
central
fallback
local
```

Change mode from the UI or with:

```bash
curl -X POST http://127.0.0.1:8088/api/operator/mode/central
curl -X POST http://127.0.0.1:8088/api/operator/mode/fallback
curl -X POST http://127.0.0.1:8088/api/operator/mode/local
```

The webcam view draws mmWave camera-projected points. It also keeps a short
in-browser trail history per `track_id` or synthetic radar point label.

## 7. DCA1000 Raw ADC Path

For raw ADC captures, use:

```text
layer1_sensor_hub/mmwave_dca/DCA1000_CLI_TEST_COMMANDS.md
```

UART/TLV is still the fastest path for Phase 2 UI demos. DCA1000 is for deeper
offline radar analysis and Range-Doppler work.
