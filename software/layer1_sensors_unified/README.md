# Layer 1 - Unified Sensors (Non-Primary)

This package groups all non-primary Layer 1 sensor modules in one place:

- `aux_sensors` (ESP32 / auxiliary serial sensors)
- `thermal_camera` (thermal stream and processing)
- `radar_presence_60g` (Infineon XENSIV `BGT60LTR11AIP` 60 GHz presence path)

The primary radar path remains isolated in `software/layer1_radar`.

## Shared Port Scanner

To avoid duplicated serial-port discovery logic, this package provides a common scanner:

- `common.port_scanner.PortScanner`
- `common.port_scanner.PortInfo`

Sensor-specific matching is implemented by dedicated resolvers:

- `aux_sensors.port_resolver.AuxSensorPortResolver`
- `radar_presence_60g.port_resolver.Presence60GPortResolver`
