# Layer 7: Alerts

## Objective
Build, present, serialize, and log alerts from system state events.

## Inputs
- `StateEvent` from Layer 6.

## Outputs
- `AlertPayload(level, message, metadata)`.

- Text render for E-Ink.

- Serialized payload for LoRa (`bytes`).

- `EventRecord` persisted in memory.

## `.py` Files
- `alert_manager.py`: builds normalized payload.

- `eink_driver.py`: renders payload to string.

- `lora_sender.py`: compact JSON serialization.

- `event_logger.py`: in-memory logger with ISO UTC timestamp.

- `__init__.py`: public exports.

## Recommended Flow
1. `AlertManager` transforms `StateEvent` into `AlertPayload`.

2. `EInkDriver` generates a visual message.

3. `LoRaSender` serializes the event for transport.

4. `EventLogger` logs the event history.

## Exit Criteria (DoD)
- Consistent payload across multiple channels.

- Compact and stable serialization.

- Logging available for auditing and smoke testing.