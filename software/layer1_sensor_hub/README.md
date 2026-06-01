# Layer 1 Sensor Hub

Unified Layer 1 entrypoint for three sensors:

- `mmwave`: TI IWR6843 UART + TLV
- `mmwave_dca`: TI IWR6843/AWR1843 raw ADC capture through DCA1000EVM
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
- `mmwave_dca` is for LVDS/DCA1000 raw ADC capture and writes `adc_data.bin`.
- `testing/ADRIAN_PHASE2_RUNBOOK.md` lists Adrian's Phase 2 mmWave/UI commands and API checks.






mmWave Data Ingestion Setup
mmWave Parsing & Object Extraction
mmWave Visualization (basic overlay points)
Sensor Fusion (mmWave → camera mapping basic)
Improved mmWave Visualization (movement vectors)
UI Base Setup (React app skeleton)
Live Camera Feed Component
Detection Overlay UI (bounding boxes)
Device Listing UI (CCTV/Ring style grid)

Frontend UI with Device listing like ring UI or CCTV camera UI.
Alert UI (weapon detection indicators)
UI Metrics Panel (FPS, latency display)
UI + mmWave overlay integration
Enhanced Visualization (trajectory preview UI)
UI Status Indicators (device health)
UI Controls (toggle modes, configs)
Failure State UI (alerts, warnings)
UI Auto-refresh + reconnection logic
Recovery UI indicators
Alert Visualization Improvements
Config Panel UI
Tracking Visualization (IDs + paths)
UI Path Rendering (lines/trails)
Unsafe Person Highlight UI
