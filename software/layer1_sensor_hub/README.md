# Layer 1 Sensor Hub

Unified Layer 1 entrypoint for three sensors:

- `mmwave`: TI IWR6843 UART + TLV
- `infeneon`: 60 GHz LTR11 presence provider
- `thermal`: thermal camera frame source

## Goals

- Keep `layer1_sensor_hub` independent from `layer1_radar`
- Provide one place to read all enabled sensors per cycle
- Preserve per-sensor modules for low-level debugging

## Quick Start

```python
from software.layer1_sensor_hub.mmwave import SerialManager, RadarConfigurator, UARTSource, TLVParser
from software.layer1_sensor_hub.infeneon import MockPresenceProvider, PresenceSource
from software.layer1_sensor_hub.thermal import ThermalCameraSource
from software.layer1_sensor_hub import MultiSensorHub

# mmWave setup
serial_mgr = SerialManager()
ports = serial_mgr.find_radar_ports()
serial_mgr.connect(ports.config_port, ports.data_port)
RadarConfigurator(serial_mgr).configure()  # default config
mmw_source = UARTSource(serial_mgr)
mmw_parser = TLVParser()

# Presence setup (replace mock with IfxLtr11PresenceProvider on hardware)
presence_source = PresenceSource(MockPresenceProvider())

# Thermal setup
thermal = ThermalCameraSource(device=0)

hub = MultiSensorHub(
    mmwave_source=mmw_source,
    mmwave_parser=mmw_parser,
    presence_source=presence_source,
    thermal_source=thermal,
)

frame = hub.read_frame(mmwave_timeout_ms=200)
print(frame.frame_number, frame.timestamp_ms)
print("mmWave parsed:", frame.mmwave_frame is not None)
print("presence:", frame.presence_frame is not None)
print("thermal:", frame.thermal_frame_bgr is not None)

hub.close()
serial_mgr.disconnect()
```

## Notes

- `RadarConfigurator.configure()` now accepts `None` and defaults to `DEFAULT_CONFIG`.
- `mmwave` config commands now fail fast if command response is empty.
- `UARTSource` includes small idle sleeps to avoid busy-loop CPU usage when no data is available.
