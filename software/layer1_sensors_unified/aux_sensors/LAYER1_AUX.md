# Layer 1 - Auxiliary Sensors

## Objective
Ingest non-radar auxiliary sensors (e.g., PIR, RF trigger modules, thermal probe sensors) through a lightweight serial bridge and typed protocol.

## Inputs
- Newline-delimited JSON messages from an ESP32 (USB serial).

## Outputs
- `AuxFrame` messages with typed `AuxReading` entries.
- `AuxHeartbeat` messages for link health.

## Files
- `config.py`: serial and health watchdog settings.
- `sensor_models.py`: typed dataclasses for readings, frames, heartbeat.
- `serial_bridge.py`: serial connect/read/write transport.
- `aux_protocol.py`: JSON line parser/encoder.
- `aux_source.py`: orchestration and frame streaming.
- `health_monitor.py`: stream health status.
- `__init__.py`: public exports.

## Recommended Flow
1. Open serial with `SerialBridge`.
2. Read lines in `AuxSensorSource`.
3. Parse with `AuxProtocol`.
4. Emit `AuxFrame` into fusion pipeline.

## DoD
- Typed and deterministic parsing.
- Graceful handling for empty/invalid lines.
- Health status available for monitoring.
