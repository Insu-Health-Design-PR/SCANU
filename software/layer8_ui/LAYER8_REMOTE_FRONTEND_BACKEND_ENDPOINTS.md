# Layer 8 Remote Frontend -> Jetson Backend Endpoints

This document explains what the Layer 8 frontend needs when it runs on a different host than the backend (Jetson).

Jetson backend base URL (default):

```text
http://<JETSON_IP>:8088
```

WebSocket URL:

```text
ws://<JETSON_IP>:8088/ws/events
```

## Required Endpoints Used by Frontend

## 1) `GET /api/status`
- Purpose: system state for dashboard header/cards (`state`, `fused_score`, `confidence`, health summary, active radars).
- Why frontend needs it: drives main runtime state (SCANNING/IDLE) and confidence values.
- Data source: sensor runner status + Layer 6 orchestration/fusion outputs.

## 2) `GET /api/health`
- Purpose: simplified health (`healthy`, `has_fault`, `sensor_online_count`).
- Why frontend needs it: health badges/indicators.
- Data source: derived from status/runner health in backend.

## 3) `GET /api/alerts/recent?limit=50`
- Purpose: recent alert log list.
- Why frontend needs it: Console Log panel.
- Data source: Layer 7 alert bridge + backend fallback events.

## 4) `GET /api/visual/latest`
- Purpose: latest visual payload in one response.
- Fields used by frontend:
  - `rgb_jpeg_b64`
  - `thermal_jpeg_b64`
  - `point_cloud`
  - `presence`
  - `timestamp_ms`
  - `source_mode`
- Why frontend needs it: initializes RGB/Thermal/PointCloud/Presence views.
- Data source:
  - RGB frame from webcam stream/live frame artifact
  - Thermal frame from thermal stream/live frame artifact
  - Point cloud from mmWave artifact output
  - Presence/confidence from live metrics.

## 5) `GET /api/ui/preferences`
- Purpose: load UI layout preferences.
- Why frontend needs it: restores selected layout/style/modules.
- Data source: Layer 8 local preferences storage.

## 6) `POST /api/ui/preferences`
- Purpose: save UI layout preferences.
- Why frontend needs it: persist user layout changes.
- Data source: writes into Layer 8 preference storage.

## 7) `POST /api/control/reconfig`
- Purpose: execute Start/Stop/Reconfigure actions from Execution Controls.
- Why frontend needs it: control sensors from UI.
- Data source: backend maps request to sensor runner actions (`run_all`, `stop_all`, `restart_all` behavior).

## 8) `POST /api/control/reset-soft`
- Purpose: soft reset from UI.
- Why frontend needs it: quick runtime recovery action.
- Data source: backend restart logic for sensors.

## 9) `WS /ws/events`
- Purpose: real-time updates.
- Event types used by frontend:
  - `status_update`
  - `visual_update`
  - `sensor_fault`
  - `alert_event`
  - `control_result`
- Why frontend needs it: live dashboard without waiting for polling interval.
- Data source: periodic backend event stream composed from status + visuals + faults + control outcomes.

## Optional but Useful Endpoints

- `GET /api/layers/summary`: cross-layer integration validation (Layer 1..8).
- `GET /api/system/metrics`: host metrics for operational dashboards.
- `GET /api/visual/rgb`, `GET /api/visual/thermal`, `GET /api/visual/point-cloud`, `GET /api/visual/presence`: split visual endpoints for debugging.

## Remote Deployment Pattern (Frontend in another host)

Set these env vars where frontend runs:

```bash
VITE_LAYER8_API_BASE="http://<JETSON_IP>:8088"
VITE_LAYER8_WS_URL="ws://<JETSON_IP>:8088/ws/events"
```

Why this is required:
- Prevents frontend from using `localhost` (which would point to the frontend host, not Jetson).
- Forces API/WS traffic to Jetson backend.

## Quick Validation Checklist

From the frontend host:

```bash
curl -sS http://<JETSON_IP>:8088/api/health
curl -sS http://<JETSON_IP>:8088/api/status
curl -sS http://<JETSON_IP>:8088/api/visual/latest
curl -sS "http://<JETSON_IP>:8088/api/alerts/recent?limit=10"
```

Expected:
- HTTP 200 on all endpoints.
- Non-empty JSON responses.

WebSocket check (basic):

```text
ws://<JETSON_IP>:8088/ws/events
```

Expected:
- connection opens
- receives `status_update` and `visual_update` events.

## CORS Note

Layer 8 backend currently enables permissive CORS middleware (`allow_origins=["*"]`), so cross-origin frontend access is allowed by default.

