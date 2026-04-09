# L6 -> L7 -> L8 Integration Plan (Temporary)

## Summary
This plan defines the post-validation integration path from Layer 6 (state/control) into Layer 7 (alerts/logging) and Layer 8 (backend/UI stream), using the current `Layer6Orchestrator` outputs (`StateEvent`, `StateSnapshot`, optional `ActionRequest`).

Success means:
- Layer 7 receives and transforms Layer 6 events into normalized alerts.
- Layer 8 exposes current status + live stream + recent alert history.
- End-to-end scenarios (normal, anomaly, fault, recovery) are visible in backend outputs and UI stream.

## Implementation Changes

### 1) Layer 7 alert pipeline
- Implement an `AlertManager` that maps `StateEvent.current_state` into alert levels:
  - `IDLE` -> `INFO`
  - `TRIGGERED` / `SCANNING` -> `WARNING`
  - `ANOMALY_DETECTED` -> `ALERT`
  - `FAULT` -> `FAULT`
- Emit a typed `AlertPayload` with:
  - `event_id`, `timestamp_utc`, `level`, `state`, `message`, `radar_id`, `scores`, `metadata`
- Add an `EventLogger` (append-only) for audit + replay and expose query helpers:
  - `append(payload)`
  - `recent(limit)`
  - `by_level(level, limit)`

### 2) Layer 8 backend stream integration
- Add backend contracts for:
  - latest `StateSnapshot`
  - latest `AlertPayload`
  - recent alerts list
- Add API endpoints:
  - `GET /api/status`
  - `GET /api/alerts/recent`
  - `GET /api/health`
- Add WebSocket event encoding with event types:
  - `status_update`
  - `alert_event`
  - `sensor_fault`
  - `heartbeat`
- Ensure Layer 6 tick loop pushes state and alerts to backend publisher.

### 3) Layer 6 integration hooks
- Keep Layer 6 APIs unchanged.
- Add a lightweight integration adapter that forwards:
  - `StateEvent` -> Layer 7 `AlertManager`
  - `StateSnapshot` -> Layer 8 status store
- Preserve `ActionRequest` flow for operational actions (e.g., soft reset recommendation on fault).

### 4) Operational wiring
- Extend current runtime/runner flow so one command can:
  - run Layer 6 loop
  - generate Layer 7 alerts
  - publish Layer 8 status/stream
- Keep destructive control actions manual-only (`kill`, `usb-reset`), unchanged from current policy.

## Public Interfaces (New/Updated)
- `AlertManager.build(state_event) -> AlertPayload`
- `EventLogger.append(payload) -> None`
- `EventLogger.recent(limit=50) -> list[AlertPayload]`
- `BackendStateStore.update_status(snapshot) -> None`
- `BackendStateStore.publish_alert(payload) -> None`
- `WebSocketStream.encode_status(snapshot) -> dict`
- `WebSocketStream.encode_alert(payload) -> dict`

## Test Plan
1. Unit tests:
- state-to-alert mapping for all `SystemState` values
- alert payload schema completeness
- logger append/recent ordering
- websocket encoding for status/alert events

2. Integration tests:
- L6 tick -> L7 payload generated
- L6 tick -> L8 status updated
- anomaly scenario emits `ALERT`
- fault scenario emits `FAULT` and recovery path updates status correctly

3. End-to-end smoke:
- run in simulate mode and verify:
  - `/api/status` changes over time
  - `/api/alerts/recent` receives expected records
  - websocket stream emits `status_update` and `alert_event`

## Assumptions and Defaults
- Keep current Layer 6 contracts unchanged to avoid rework.
- Use existing provisional L1/L2 fusion input until Layer 5 real output is connected.
- Initial persistence can be in-memory (or local JSON/SQLite) as long as retrieval APIs are stable.
- This document is temporary and should be replaced by implementation notes after validation passes.
