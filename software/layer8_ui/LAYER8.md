# Layer 8: UI / Backend Stream

## Objective
Expose operational status and alert events for UI/service consumption via API and streaming.

## Inputs
- Status and score from Layer 6/5.

- `AlertPayload` from Layer 7.

## Outputs
- `SystemStatus` in `dict` format for the backend.

- WebSocket events encoded in compact JSON.

## `.py` Files
- `backend_api.py`: stores the current status and last alert.

- `websocket_stream.py`: encodes events for the stream.

- `__init__.py`: public exports.

## Recommended Flow
1. Update status with `BackendAPI.update_status()`.

2. Publish alerts with `BackendAPI.publish_alert()`.

3. Expose snapshot with `get_status()`.

4. Publish to the channel in real time via `WebSocketStream.encode()`.

## Exit Criteria (DoD)
- Status and alerts accessible as simple contracts.

- Compact and deterministic JSON stream format.

- Full integration with L2->L7 pipeline in smoke tests.
