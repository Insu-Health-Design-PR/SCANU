# AGENTS.md — Context for AI Assistants

## Project: SCAN-U — Concealed Object Detection with mmWave Radar

### Mission

Use **raw mmWave ADC data** (captured via DCA1000) to:
1. **Improve firearm detection** — leverage raw I/Q samples for custom Range-Doppler processing, MTI filtering, and coherence analysis beyond what the TI TLV pipeline offers
2. **Generate point clouds** of concealed weapons — process raw ADC into 3D point clouds for visualizing hidden objects on the body

### Project Structure

```
software/
├── layer1_radar/           ← Radar drivers (mmWave SDK, Infineon)
│   └── mmwave/             ← TI radar constants
├── layer1_sensor_hub/      ← Sensor hub (radar, thermal camera)
│   ├── mmwave_dca/         ← ★ DCA1000 module (raw ADC capture)
│   │   ├── dca1000_control.py     ← DCA1000 UDP control
│   │   ├── dca1000_udp.py         ← UDP data receiver
│   │   ├── capture_runner.py      ← Capture orchestrator
│   │   ├── run_dca_capture.py     ← CLI entrypoint
│   │   ├── run_jetson_native_capture.sh ← Shell script
│   │   ├── adc_reader.py          ← ADC data reading & processing
│   │   ├── process_adc_file.py    ← CLI for Range-Doppler PNG
│   │   ├── diagnose_dca1000.py    ← Connectivity diagnostic
│   │   ├── radar_cli.py           ← Radar UART CLI config
│   │   ├── multi_sensor.py        ← Multi-sensor capture
│   │   ├── ti_cli/configFile.json ← DCA1000 JSON config
│   │   ├── DCA1000_CAPTURE_GUIDE.md ← ★ Capture guide (EN)
│   │   └── CAPTURE_TESTS.md       ← ★ Test results (EN)
│   └── testing/configs/    ← Radar .cfg files
│       ├── weapon_detection_dca1000.cfg  ← ★ Default for DCA1000
│       ├── dca1000_adc_capture.cfg       ← Basic ADC config
│       └── ...other .cfg...
├── layer3_features/        ← Feature processing
├── layer6_state_machine/   ← State machine
└── layer7_alerts/          ← Alert system
```

### ★ Changes made to dca1000_control.py

Three bugs fixed that prevented DCA1000 communication:

1. **Source port** (line 201):
   - BEFORE: `sock.bind((self.network.pc_ip, 0))` — ephemeral port
   - AFTER: `sock.bind((self.network.pc_ip, self.network.config_port))` — port 4096
   - DCA1000 only responds when UDP source port is 4096.

2. **connect_first** (line 240):
   - BEFORE: `connect_first: bool = True`
   - AFTER: `connect_first: bool = False`
   - This DCA1000 firmware doesn't implement SYSTEM_CONNECT (0x09).
   - Correct sequence: reset_fpga → fpga → packet (no connect).

3. **Response validation** (line 278, `_response_ok`):
   - BEFORE: Checked last 2 bytes of "status_region" were zero.
   - AFTER: Verifies packet footer is 0xEEAA.
   - READ_FPGA_VERSION response has non-zero payload data that was falsely flagged as error.

### How to run DCA1000 capture

Always use PYTHONPATH:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software
export PYTHONPATH=/home/insu/Desktop/SCANU-dev_adrian/software:$PYTHONPATH
```

**Diagnostic:**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.diagnose_dca1000
```

**Quick capture:**
```bash
CLI_PORT=/dev/ttyUSB0 DURATION_S=5 \
./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

**Manual capture:**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port /dev/ttyUSB0 \
  --config layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg \
  --dca-config layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
  --output captures/adc_data.bin --duration-s 5 \
  --configure-dca --start-dca --stop-dca
```

**Process data:**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.process_adc_file \
  --input captures/adc_data.bin \
  --frames 100 --chirps 16 --rx 4 --samples 384 \
  --allow-truncate --output captures/range_doppler.png
```

### DCA1000 Protocol

- **Commands** (UDP port 4096): `0xA55A | cmd(2B LE) | len(2B LE) | payload | 0xEEAA`
- **Data** (UDP port 4098): `[10B header] [ADC data ~1456B]`
- **ADC format**: TI interleaved — `I0,I1,I2,I3,Q0,Q1,Q2,Q3` per sample (4 RX)
- **Rate**: ~2000 pkt/s, ~2.79 MB/s, 1456 bytes/payload fixed

### Hardware

| Device | Connection | IP/Port |
|---|---|---|
| Jetson | — | 192.168.33.30 |
| DCA1000 | Ethernet eth0 | 192.168.33.180:4096/4098 |
| Radar IWR6843 | USB (/dev/ttyUSB0) | UART CLI |

### Important notes

- `run_jetson_native_capture.sh` has a path bug: `SOFTWARE_DIR` points to project root, not `software/`. Use absolute paths via `RADAR_CFG`, `DCA_CFG`, `OUTPUT`.
- `captures/` and `*.bin` are in `.gitignore`.
- PYTHONPATH always required to run modules.
- Test captures showed consistent ADC data (noise ~200 LSB, no saturation, ~2000 pkt/s).
