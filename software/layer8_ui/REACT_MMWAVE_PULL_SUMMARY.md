# Pull Summary: React Layer 8 + mmWave Operator UI

## Summary

This pull adds the Phase 2 Adrian workflow foundation:

```text
mmWave data -> normalized objects -> top-down preview -> camera overlay -> React operator UI
```

The existing FastAPI backend remains the Layer 8 API server. A new React/Vite
frontend is served from `layer8_ui/frontend/dist` when built, with the legacy
static dashboard retained only as fallback.

## Main Changes

- Added React/Vite operator UI under `software/layer8_ui/frontend`.
- Added mmWave normalization helpers for stable frame/object contracts.
- Added mmWave top-down preview rendering and camera projection helpers.
- Added Layer 8 endpoints:
  - `/api/mmwave/latest`
  - `/api/mmwave/frames`
  - `/api/mmwave/camera-overlay`
  - `/api/mmwave/preview/regenerate`
  - `/api/devices`
  - `/api/operator/state`
  - `/api/operator/mode/{central|fallback|local}`
- Added React UI panels for:
  - live webcam/thermal feed
  - mmWave overlay dots
  - short tracking trails
  - device grid
  - metrics
  - alerts
  - operator mode/recovery state
  - run/stop/restart/config controls
- Updated `layer8.sh` with a `frontend` command and automatic React build during setup.
- Added Adrian Phase 2 runbook with mmWave, React, overlay, and DCA1000 notes.

## Verification

Commands run:

```bash
npm run build
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  software/layer1_sensor_hub/testing/test_mmwave_normalized.py \
  software/layer1_sensor_hub/testing/test_mmwave_dca_adc_reader.py \
  software/layer1_sensor_hub/testing/test_sensor_hub.py \
  software/layer1_sensor_hub/testing/test_run_live_hub.py \
  software/layer1_sensor_hub/testing/test_testing_scripts.py \
  software/layer8_ui/testing/test_react_frontend_serving.py
```

Result:

```text
vite build OK
15 passed
```

API smoke checks:

```text
/api/operator/state 200
/api/devices 200
/api/mmwave/camera-overlay 200
```

## Not Included

- `node_modules/` and `frontend/dist/` are intentionally ignored.
- TI mmWave Studio installer and raw `.bin` captures are intentionally ignored.
- Hardware validation is still required on Jetson with radar and camera connected.

## Remaining Hardware/Integration Work

- Validate React dashboard on Jetson browser.
- Run real radar UART/TLV capture.
- Calibrate mmWave projection over webcam.
- Validate model bounding boxes with real camera feed.
- Integrate real ByteTrack `track_id` values when backend is ready.
- Validate fallback/recovery behavior once server-side fallback logic is available.
