# Layer 8 Frontend (Scaffold)

This folder is the dedicated frontend workspace for the new Layer 8 UI.

## Planned stack
- React 18
- TypeScript
- Vite

## Backend contracts to consume
- `GET /api/status`
- `GET /api/health`
- `GET /api/alerts/recent`
- `WS /ws/events`

## Next implementation steps
1. Initialize Vite React+TS app.
2. Build status panel (state, fused score, confidence).
3. Build health panel (fault, sensor count).
4. Build alerts table from `/api/alerts/recent`.
5. Add websocket live updates for `status_update` and `alert_event`.
