# DCA1000 Capture Guide — SCAN-U

## Hardware Setup

```
Radar IWR6843 LVDS  → DCA1000EVM (ribbon cable)
Radar IWR6843 USB   → Jetson USB  (/dev/ttyUSB0)
DCA1000 Ethernet    → Jetson eth0 (direct)
DCA1000 power       → 12V DC
Radar power         → 5V DC
```

## 1. Verify Connections

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

# Full diagnostic
PYTHONPATH=. python3 -m layer1_sensor_hub.mmwave_dca.diagnose_dca1000

# Manual checks:
ls /dev/ttyUSB* /dev/ttyACM*          # Serial ports
ip addr show eth0                      # Jetson IP (must be 192.168.33.30)
ip neigh show dev eth0                 # DCA1000 ARP (192.168.33.180)
```

## 2. Configure Network (first time or after reconnect)

```bash
sudo ip addr flush dev eth0
sudo ip addr add 192.168.33.30/24 dev eth0
sudo ip link set eth0 up
```

## 3. One-Command Capture

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

CLI_PORT=/dev/ttyUSB0 \
DURATION_S=5 \
RADAR_CFG=/home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg \
DCA_CFG=/home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
OUTPUT=/home/insu/Desktop/SCANU-dev_adrian/captures/adc_data.bin \
./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `CLI_PORT` | auto-detect | Radar serial port (`/dev/ttyUSB0`) |
| `ETH_DEV` | `eth0` | Ethernet interface |
| `JETSON_IP` | `192.168.33.30` | Jetson IP address |
| `DCA_IP` | `192.168.33.180` | DCA1000 IP address |
| `DURATION_S` | `5` | Capture duration in seconds |
| `RADAR_CFG` | `weapon_detection_dca1000.cfg` | Radar config file |
| `DCA_CFG` | `ti_cli/configFile.json` | DCA1000 config file |
| `OUTPUT` | `captures/adc_data.bin` | Output file path |

## 4. Manual Capture (more control)

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

PYTHONPATH=. python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port /dev/ttyUSB0 \
  --config layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg \
  --dca-config layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
  --output /home/insu/Desktop/SCANU-dev_adrian/captures/adc_data.bin \
  --duration-s 5 \
  --configure-dca --start-dca --stop-dca
```

### Important Flags

| Flag | Description |
|---|---|
| `--configure-dca` | Configure DCA1000 via UDP (reset_fpga + fpga + packet) |
| `--start-dca` | Send start_record before sensorStart |
| `--stop-dca` | Send stop_record after capture |
| `--skip-radar-config` | Skip sending .cfg to radar |
| `--no-sensor-start` | Skip sensorStart command |

## 5. Process Captured Data

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

PYTHONPATH=. python3 -m layer1_sensor_hub.mmwave_dca.process_adc_file \
  --input /home/insu/Desktop/SCANU-dev_adrian/captures/adc_data.bin \
  --frames 100 --chirps 16 --rx 4 --samples 384 \
  --allow-truncate \
  --output /home/insu/Desktop/SCANU-dev_adrian/captures/range_doppler.png
```

### Parameters from .cfg file

`chirps` is calculated as: `numLoops × (endChirpIdx - startChirpIdx + 1)`

For `frameCfg 0 2 16 0 100 1 0`:
- startChirpIdx=0, endChirpIdx=2 → 3 chirp profiles
- numLoops=16 → 16 loops
- **total chirps per frame = 3 × 16 = 48**

In practice the DCA1000 packets data per loop, so `chirps=16` (numLoops) is the value used.

### Expected size formula

```
bytes = frames × chirps × rx × samples × 2 (I/Q) × 2 (int16)
      = 100 × 16 × 4 × 384 × 4 = 9,830,400 bytes (~9.4 MB)
```

## 6. ADC Data Format (TI interleaved)

The DCA1000 transmits data in **TI interleaved format**:

```
Sample 0: I0, I1, I2, I3, Q0, Q1, Q2, Q3
Sample 1: I0, I1, I2, I3, Q0, Q1, Q2, Q3
...
```

Where I0-I3 are the I (real) components of the 4 RX channels,
and Q0-Q3 are the Q (imaginary) components.

Disk order: `I0, I1, I2, I3, Q0, Q1, Q2, Q3` per sample.

## 7. Software Architecture

```
run_jetson_native_capture.sh   ← High-level bash wrapper
        │
run_dca_capture.py             ← CLI entrypoint (argparse)
        │
capture_runner.py              ← Orchestrator:
  │  1. Configure radar (radar_cli.py → UART)
  │  2. Configure DCA1000 (dca1000_control.py → UDP)
  │  3. Start recorder (dca1000_udp.py → socket)
  │  4. Start DCA1000 + sensorStart
  │  5. Capture UDP packets
  │  6. Stop DCA1000 + sensorStop
  │
  └── adc_reader.py            ← Process adc_data.bin → numpy
        │
        └── process_adc_file.py ← CLI for Range-Doppler PNG
```

### DCA1000 UDP Protocol

**Commands** (port 4096):
```
0xA55A | cmd (2B LE) | len (2B LE) | payload | 0xEEAA
```

| Command | Code | Description |
|---|---|---|
| RESET_FPGA | 0x01 | FPGA reset |
| CONFIG_FPGA_GEN | 0x03 | Configure FPGA (LVDS, format) |
| CONFIG_PACKET_DATA | 0x0B | Inter-packet delay |
| RECORD_START | 0x05 | Start recording |
| RECORD_STOP | 0x06 | Stop recording |
| READ_FPGA_VERSION | 0x0E | Read FPGA version |

**Data** (port 4098):
```
[10-byte header: seq(4) + byte_count(4) + reserved(2)] [ADC data...]
```

Each UDP packet contains ~1456 bytes of ADC data (after header removal).

## 8. Troubleshooting

| Issue | Likely cause |
|---|---|
| DCA1000 no UDP response | Wrong source port (must be 4096) |
| `connect` fails | Firmware doesn't support SYSTEM_CONNECT (0x09) |
| Empty .bin file | DCA1000 not started or sensorStart before recorder |
| 0 packets | Ethernet cable, IP, or LVDS not enabled |
| `ModuleNotFoundError` | Missing PYTHONPATH=. |
