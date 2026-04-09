# Layer 8 Frontend (Industrial Ops)

Primary operator console for SCAN-U Layer 8 backend.

## Stack
- React 18
- TypeScript
- Vite
- React Router

## Routes
- `/dashboard`: live status, sensor cards, alerts, score trend, state timeline
- `/control`: sensor/radar control actions and command output log
- `/events`: alert history with filters and JSON export

## Backend Contracts Used
- `GET /api/status`
- `GET /api/health`
- `GET /api/alerts/recent`
- `GET /api/sensors/status`
- `GET /api/sensors/status/{radar_id}`
- `POST /api/control/reconfig`
- `POST /api/control/reset-soft`
- `POST /api/control/kill-holders`
- `POST /api/control/usb-reset`
- `WS /ws/events`

## WS Event Types Used
- `status_update`
- `alert_event`
- `sensor_fault`
- `heartbeat`
- `control_result`

## Operator Modes
- `monitor`: read-only
- `control`: safe controls enabled (`status`, `reconfig`, `reset_soft`)
- `maintenance`: destructive controls enabled (`kill_holders`, `usb_reset`) with confirmation modal

## Dev Commands
```bash
cd software/layer8_ui/frontend
npm install
npm run dev
```

Full validation command set: see `TEST_COMMANDS.md`.

Optional environment variables:
- `VITE_API_BASE` (default: same host)
- `VITE_WS_BASE` (default: same host `/ws/events`)

## Keyboard Shortcuts
- `r`: refresh from REST
- `g`: go to dashboard
- `c`: go to control
