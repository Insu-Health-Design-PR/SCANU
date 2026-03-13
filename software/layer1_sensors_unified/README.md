# Layer 1 - Unified Sensors (Non-Primary)

This package groups all non-primary Layer 1 sensor modules in one place:

- `aux_sensors` (ESP32 / auxiliary serial sensors)
- `thermal_camera` (thermal stream and processing)
- `radar_presence_60g` (Infineon 60 GHz presence path)

The primary radar path remains isolated in `software/layer1_radar`.
