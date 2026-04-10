# Layer 8: Operator Dashboard and Backend Stream

## Objective
Expose real-time system status, anomaly trends, sensor health, and alert history through a backend API and live stream for the operator dashboard.

## Folder Layout
- `backend/`: official Layer 8 backend (FastAPI + WS + L6/L7 bridge).
- `frontend/`: new React/TS/Vite workspace (scaffold, implementation pending).
- `legacy/`: previous sensor-runner UI and capture tooling kept for operational diagnostics.
- root wrappers (`app.py`, `run_layer8.py`, etc.): compatibility shims that forward to `backend/`.

## Backend Inputs
- `StateSnapshot` from Layer 6.
- `AlertPayload` from Layer 7.
- Optional `ActionRequest` for fault operation context.

## Backend Contracts
- `GET /api/status`
- `GET /api/health`
- `GET /api/alerts/recent?limit=50`
- `GET /api/sensors/status`
- `GET /api/sensors/status/{radar_id}`
- `GET /api/visual/latest`
- `GET /api/visual/rgb`
- `GET /api/visual/thermal`
- `GET /api/visual/point-cloud`
- `GET /api/visual/presence`
- `POST /api/control/reconfig`
- `POST /api/control/reset-soft`
- `POST /api/control/kill-holders`
- `POST /api/control/usb-reset`
- `WS /ws/events`

## WS Event Types
- `status_update`
- `alert_event`
- `sensor_fault`
- `heartbeat`
- `control_result`
- `visual_update`

## Main Backend Modules
- `backend/backend_state_store.py`
- `backend/status_models.py`
- `backend/websocket_stream.py`
- `backend/publisher.py`
- `backend/integration.py`
- `backend/app.py`
- `backend/run_layer8.py`
- `backend/run_layer8_stack.py`

## Integration Flow
1. Layer 6 emits `StateEvent`, `StateSnapshot`, optional `ActionRequest`.
2. Layer 7 maps event to `AlertPayload`.
3. Layer 8 backend stores latest status + alert history.
4. Layer 8 backend pushes WS updates to UI clients.

## Current Status
- Backend implemented and tested.
- Legacy tooling preserved under `legacy/`.
- Frontend directory scaffold exists; operator UI implementation is still pending.
