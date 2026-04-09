# Layer 7: Alerting and Event Logging

## Objective
Build, serialize, route, and persist alert events derived from state transitions for operator visibility and external notification channels.

## Inputs
- StateEvent from Layer 6
- Optional StateSnapshot for context

## Outputs
- AlertPayload(level, message, metadata)
- E-Ink render payload (human-readable text)
- LoRa transport payload (compact bytes)
- EventRecord persisted in in-memory or durable log store

## Alert Levels
- INFO
- WARNING
- ALERT
- FAULT

## Responsibilities
- Convert state transitions into normalized alert payloads
- Render concise operator messages for E-Ink or local display
- Serialize compact payloads for LoRaWAN transmission
- Persist event records with UTC timestamps
- Deduplicate or rate-limit repeated alerts

## Recommended Python Files
- alert_manager.py: state to alert mapping
- eink_driver.py: concise text rendering for display
- lora_sender.py: compact JSON or msgpack serialization
- event_logger.py: append-only event history and query API
- __init__.py: exports

## Payload Contract
Minimum fields:
- event_id
- timestamp_utc
- level
- state
- message
- fused_score
- confidence
- source_summary

## Delivery Rules
- Always log every state transition event
- Notify ALERT and FAULT immediately
- Coalesce repeated INFO and WARNING within a short window

## Recommended Flow
1. Receive StateEvent.
2. Build AlertPayload from transition and context.
3. Render E-Ink text payload.
4. Serialize LoRa payload and enqueue for transport.
5. Persist EventRecord with canonical UTC timestamp.
6. Publish latest alert to Layer 8 backend stream.

## Observability
Track channel-level metrics:
- alerts_total by level
- dropped_or_coalesced_count
- lora_send_attempts and failures
- end-to-end alert latency

## Definition of Done (DoD)
- Normalized alert contract implemented
- E-Ink and LoRa serializers implemented and tested
- Event logger supports retrieval for audit and UI
- Deduplication and rate-limit policy verified
- Integration validated with Layer 6 input and Layer 8 publishing
