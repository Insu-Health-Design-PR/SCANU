# Layer 8: Operator Dashboard and Backend Stream

## Objective
Expose real-time system status, anomaly trends, sensor health, and alert history through a backend API and live stream for the React operator dashboard.

## Runtime Target
- Edge host: Jetson Orin Nano
- Backend: FastAPI service
- Frontend: React plus TypeScript

## Inputs
- `StateSnapshot` from Layer 6
- `AlertPayload` from Layer 7
- Optional `ActionRequest` context for fault operations

## Outputs
- REST status snapshots for polling clients
- WebSocket event stream for live UI updates
- Recent alert history for operator review

## Implemented Backend Contracts
- `GET /api/status`
- `GET /api/health`
- `GET /api/alerts/recent?limit=50`
- `WS /ws/events`

## Implemented Stream Event Types
- `status_update`
- `alert_event`
- `sensor_fault`
- `heartbeat`

## Implemented Python Modules
- `backend_state_store.py`: latest snapshot + alert history store
- `status_models.py`: response models and serializers
- `websocket_stream.py`: typed websocket encoding helpers
- `publisher.py`: in-process pub/sub for websocket fan-out
- `integration.py`: bridge from L6/L7 outputs into Layer 8
- `app.py`: FastAPI app factory and route wiring
- `run_layer8.py`: backend service runner
- `run_layer8_stack.py`: integrated L6->L7->L8 runtime demo

## Integration Path
1. Layer 6 produces `StateEvent` + `StateSnapshot` (+ optional `ActionRequest`).
2. Layer 7 builds `AlertPayload` from `StateEvent`.
3. Layer 8 bridge stores current status and alert history.
4. Layer 8 publishes websocket events for operator UI.
5. React dashboard consumes REST + WS channels.

## Definition of Done (Current)
- FastAPI backend contracts implemented
- WebSocket stream contract implemented
- In-memory status + alert store implemented
- L6->L7->L8 integration bridge implemented
- Unit tests cover store, stream encoding, integration, and API routes
