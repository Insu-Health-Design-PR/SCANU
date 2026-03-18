# Layer 1: Radar Control & Data Acquisition

This module handles communication with the TI IWR6843AOPEVM mmWave radar.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Layer 1                                 │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │ SerialManager│──►│ RadarConfig  │──►│ UARTSource   │        │
│  │              │   │              │   │              │        │
│  │ Find ports   │   │ Send CLI     │   │ Read frames  │        │
│  │ Connect      │   │ commands     │   │ Sync magic   │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│                                               │                 │
│                                               ▼                 │
│                                        ┌──────────────┐        │
│                                        │ TLVParser    │        │
│                                        │              │        │
│                                        │ Extract:     │        │
│                                        │ - Points     │        │
│                                        │ - Range      │        │
│                                        │ - Stats      │        │
│                                        └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
cd software/layer1_radar
pip install -r requirements.txt
```

## Quick Start

```python
from layer1_radar import (
    SerialManager,
    RadarConfigurator,
    UARTSource,
    TLVParser,
)

# 1. Connect to radar
serial_mgr = SerialManager()
ports = serial_mgr.find_radar_ports()  # or pass explicit CLI/DATA ports (see below)
serial_mgr.connect(ports.config_port, ports.data_port)

# 2. Configure radar
configurator = RadarConfigurator(serial_mgr)
configurator.configure()  # Uses default config

# 3. Capture and parse frames
uart_source = UARTSource(serial_mgr)
parser = TLVParser()

for raw_frame in uart_source.stream_frames(max_frames=100):
    parsed = parser.parse(raw_frame)
    
    print(f"Frame {parsed.frame_number}: {len(parsed.points)} objects")
    for point in parsed.points:
        print(f"  - ({point.x:.2f}, {point.y:.2f}, {point.z:.2f}) @ {point.doppler:.2f} m/s")

# 4. Cleanup
configurator.stop()
serial_mgr.disconnect()
```

## Modules

### `serial_manager.py`

Handles serial port discovery and connection.

```python
from layer1_radar import SerialManager

mgr = SerialManager()

# List all ports
ports = mgr.list_all_ports()

# Find radar automatically
radar_ports = mgr.find_radar_ports()

# Connect
mgr.connect(radar_ports.config_port, radar_ports.data_port)

# Use as context manager
with SerialManager() as mgr:
    # ...
```

### `radar_config.py`

Sends CLI commands to configure the radar.

```python
from layer1_radar import RadarConfigurator, DEFAULT_CONFIG

configurator = RadarConfigurator(serial_mgr)

# Use default config
configurator.configure()

# Or custom config string
configurator.configure("""
sensorStop
flushCfg
...
sensorStart
""")

# Or from file
configurator.configure_from_file('my_config.cfg')

# Control
configurator.stop()
configurator.start()
```

### `uart_source.py`

Reads raw frames from the data port.

```python
from layer1_radar import UARTSource

source = UARTSource(serial_mgr)

# Read single frame
frame = source.read_frame()

# Stream frames
for frame in source.stream_frames(max_frames=100):
    process(frame)

# Get stats
print(source.get_stats())
```

### `tlv_parser.py`

Parses TLV frames into structured data.

```python
from layer1_radar import TLVParser, ParsedFrame

parser = TLVParser()
parsed = parser.parse(raw_frame)

# Access data
print(parsed.frame_number)
print(parsed.points)  # List of DetectedPoint
print(parsed.range_profile)  # numpy array
print(parsed.stats)  # dict

# Get as numpy array
point_cloud = parsed.get_point_cloud()  # Nx4 array
```

## Examples

### List Serial Ports

```bash
python examples/list_ports.py

# If you're using a UART bridge that exposes two ports, pass them explicitly
python examples/list_ports.py --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1
```

### Capture Frames

```bash
# Capture 100 frames
python examples/capture_frames.py -n 100

# Save to JSON
python examples/capture_frames.py -n 100 -o capture.json

# Use custom config
python examples/capture_frames.py -c my_config.cfg

# Verbose logging
python examples/capture_frames.py -v

# UART bridge mode (two ports):
# - CLI/config port (often "Standard")
# - DATA port (often "Enhanced")
python examples/capture_frames.py --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1
```

## Configuration

The default configuration is optimized for indoor object detection:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Frequency | 60.75 GHz | ISM band |
| Bandwidth | ~4 GHz | ~3.75 cm range resolution |
| Frame Rate | 10 FPS | 100ms frame period |
| Range | ~10m | Indoor use |
| TX Antennas | 3 | All enabled |
| RX Antennas | 4 | All enabled |

To customize, edit `DEFAULT_CONFIG` in `radar_config.py` or provide your own `.cfg` file.

## Troubleshooting

### Radar not detected

1. Check USB connection
2. Install TI XDS110 drivers (Windows)
3. Run `python examples/list_ports.py` to see available ports
4. Verify USB cable supports data (not charge-only)
5. If using a UART bridge, run capture with `--cli-port` and `--data-port`

### No frames received

1. Check configuration sent successfully
2. Verify `sensorStart` command was sent
3. Flush data port buffer before capture
4. Check baud rate (should be 921600)

### Parse errors

1. Check frame sync (magic word detection)
2. Verify radar firmware version
3. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

## Data Structures

### DetectedPoint

```python
@dataclass
class DetectedPoint:
    x: float       # meters
    y: float       # meters (range direction)
    z: float       # meters (elevation)
    doppler: float # m/s (positive = approaching)
    snr: float     # dB (if side info available)
    noise: float   # dB (if side info available)
```

### ParsedFrame

```python
@dataclass
class ParsedFrame:
    frame_number: int
    num_detected_obj: int
    num_tlvs: int
    timestamp_cycles: int
    points: List[DetectedPoint]
    range_profile: Optional[np.ndarray]
    noise_profile: Optional[np.ndarray]
    stats: Dict[str, Any]
```

## Next Steps

Once Layer 1 is working, proceed to:
- **Layer 2**: Signal processing (heatmaps, features)
- **Layer 3**: AI inference (anomaly detection)
