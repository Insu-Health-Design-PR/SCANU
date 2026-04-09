# Layer 8: Operator Dashboard and Backend Stream

## Objective
Expose real-time system status, anomaly trends, sensor health, and alert history through a backend API and live stream for the React operator dashboard.

## Runtime Target
- Edge host: Jetson Orin Nano
- Backend: FastAPI service
- Frontend: React plus TypeScript

## Inputs
- Status snapshots from Layer 6 and Layer 5
- AlertPayload events from Layer 7
- Optional diagnostics from Layer 1 and Layer 2

## Outputs
- SystemStatus snapshot endpoints for polling clients
- WebSocket stream events for live UI updates
- Historical event API for operator review and reporting

## Responsibilities
- Maintain latest state, score, and health snapshot
- Broadcast alert and status updates in near real time
- Provide compact payloads for low-latency UI rendering
- Preserve API contracts for internal and external consumers

## Recommended Python Files
- backend_api.py: in-memory state store plus API handlers
- websocket_stream.py: event encoding and channel broadcast
- status_models.py: typed response contracts
- __init__.py: exports

## Suggested Backend Endpoints
- GET /api/status
- GET /api/health
- GET /api/alerts/recent
- GET /api/metrics
- WS /ws/events

## Suggested Frontend Views
- Live range-doppler heatmap panel
- Anomaly score timeline panel
- Sensor health and connectivity panel
- Trigger and alert event log panel

## Stream Event Types
- status_update
- score_update
- alert_event
- sensor_fault
- heartbeat

## Performance Targets
- API response under 100 ms on local network
- Stream push interval 5 to 20 Hz for live panels
- UI frame update without blocking compute loop

## Recommended Flow
1. Receive status and alert updates from Layers 5 to 7.
2. Update backend snapshot cache.
3. Publish stream event to subscribed WebSocket clients.
4. Serve status and history via REST endpoints.
5. Render operator dashboard with live and historical context.

## Definition of Done (DoD)
- FastAPI backend contracts implemented
- WebSocket stream contract implemented and documented
- React dashboard shows score, health, and alerts in real time
- Stable integration from Layers 5 to 7 into UI channel
- Smoke test verifies end-to-end event propagation
