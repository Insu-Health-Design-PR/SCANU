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
│   └── multimodal_features.py  ← ★ Multi-sensor feature extractor
├── layer5_fusion/          ← Multi-sensor fusion
│   ├── fusion_adapter.py       ← Original weighted fusion
│   ├── deterministic_fusion.py ← ★ New logic-based 3-sensor fusion
│   └── models.py               ← FusionInputContract
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

### ⚠️ Radar CLI port changes on USB re-enumeration

The CP2105 USB UART on the MMWAVEICBOOST can change port after power
cycle or USB plug/unplug. The CLI port may move from `/dev/ttyUSB0` to
`/dev/ttyUSB2` (or vice versa). **Never hardcode the port** — always
auto-detect.

**All Python entrypoints now default to ``--cli-port ""`` (empty), which
auto-detects by scanning serial ports for the radar ``version`` response.**

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

**Quick capture (auto-detects CLI port):**
```bash
DURATION_S=5 \
./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

**Manual capture (auto-detects CLI port):**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
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

### Multi‑modal features (Layer 3)

`layer3_features/multimodal_features.py` — `MultiModalFeatureExtractor` + `MultiModalFeatures`:

- Extracts 29 features across 3 sensors: mmWave (14), RGB (6), Thermal (7), cross‑sensor (2)
- `deterministic_score()` — logic rule fusion (0–1) for pre‑AI deployment
- `to_vector()` → 29‑dim float32 array for Layer 4 AI training
- `to_evidence_dict()` → dict for `FusionInputContract.evidence`

Score formula (when only mmWave):
- 25% zone coherence max, 20% coherence contrast, 10% zone CFAR count
- 15% thermal cold spot, 10% thermal waist anomaly
- 5% skin concealment, 5% RGB waist anomaly, 10% phase stability

### Deterministic fusion (Layer 5)

`layer5_fusion/deterministic_fusion.py` — `DeterministicFusionAdapter`:

- Wraps `MultiModalFeatureExtractor` and produces `FusionInputContract`
- Accepts `raw_inputs` dict with keys: `mmwave_result`, `rgb_frame`, `thermal_frame`
- Trigger score = max(coherence, zone detections, cold spot, fused score)
- Used as fallback scoring until Layer 4 AI model is trained

### TDM-MIMO processing (3 TX × 4 RX = 12 virtual channels)

The radar config uses 3 TX with 16 loops = 48 chirps/frame. Previously the data was
read with 16 chirps (mixing TX modes), causing Doppler artifacts.

**Changes in `adc_reader.py`:**
- `mimo_demux()` — reshapes [48,4,384] → [16,3,4,384] (loops, TX, RX, samples)
- `mimo_range_doppler()` — TX1-only RD (clean, correct Doppler, same noise floor as legacy)
- `mimo_virtual_snapshot()` — extract complex snapshot across 12 virtual channels
- `mimo_beamform_angle()` — correlation-based angle estimation using 8 azimuth channels (TX1+RX + TX2+RX). Applies 180° phase calibration to RX2/RX4 per TX group (matching `compRangeBiasAndRxChanPhase` in cfg)
- `mimo_coherence()` — per-TX max across 4 RX (preserves weapon signature, avoids TX spatial phase washing out coherence)
- `mimo_phase_stability()` — per-TX max phase stability

**`RawAdcWeaponDetector` auto-detects MIMO:**
- 48 chirps + 4 RX → MIMO path: TX1-only RD/MTI, per-TX max coherence, 8-channel angle
- 16 chirps + 4 RX → legacy path (backward compatible)

**Angle estimation improvement:**
- Legacy: 4 RX phase slope → inaccurate (~0° always)
- MIMO: 8 virtual channels (TX1+RX1-4 + TX2+RX1-4) with phase calibration → 0° for centered person, ±20° off-center

### Detection scores on captures

| Capture | MIMO score | Legacy score | MIMO zc | MIMO ang (close) | Zone ang |
|---|---|---|---|---|---|
| person_1m_baseline | 0.820 | 0.567 | 0.660 | 19±11° | 18±4° |
| person_1m_weapon | **0.958** | **0.747** | 0.675 | 9±21° | -3±21° |
| final_noweapon | 0.949 | 0.936 | 0.721 | 7±21° | 1±15° |
| final_weapon | 0.892 | 0.816 | 0.649 | 9±36° | 21±6° |
| weapon_only_1m | 0.974 | 0.730 | 0.748 | 5±12° | -3±4° |

MIMO scores are higher (cleaner RD) but maintain weapon > no‑weapon for `person_1m`.
`final_*` still inverted — zone [90,150] = 1.17‑1.95 m doesn't align with those
captures. `weapon_only_1m` correctly scores highest.
MIMO CFAR thresholds adjusted to `threshold_scale=3.0, noise_floor_offset_db=1.5`
(from original 8.0/3.0 used by legacy).

### Capturing training data

`capture_training_sample.py` — synchronized 3-sensor capture for AI training::

```bash
# Live capture (person stands still):
python -m layer1_sensor_hub.mmwave_dca.capture_training_sample \\
    --capture --label weapon --duration 4

# From existing .bin + live cameras:
python -m layer1_sensor_hub.mmwave_dca.capture_training_sample \\
    --bin captures/person_1m_weapon.bin --label weapon --allow-truncate
```

Each capture creates a folder ``data/training/YYYYMMDD_HHMMSS_label/`` with:
- ``metadata.json`` — label, scores, params
- ``adc_data.bin`` — raw ADC (48 chirps)
- ``rgb_frame.jpg`` — RGB camera
- ``thermal_frame.png`` — thermal (16-bit)
- ``features.npz`` — feature_vectors[frames, 29], scores, label
- ``point_cloud.csv`` — all CFAR detections

To inspect/export the dataset::

```bash
python -m layer1_sensor_hub.mmwave_dca.train_data_loader --summary
python -m layer1_sensor_hub.mmwave_dca.train_data_loader \\
    --export training_data.npz
```

### Important notes

- `run_jetson_native_capture.sh` has a path bug: `SOFTWARE_DIR` points to project root, not `software/`. Use absolute paths via `RADAR_CFG`, `DCA_CFG`, `OUTPUT`.
- `captures/` and `*.bin` are in `.gitignore`.
- PYTHONPATH must include `/home/insu/Desktop/SCANU-dev_adrian` (NOT `software/`) because `sensor_control.py` imports `from software.layer1_sensor_hub...`
- Test captures showed consistent ADC data (noise ~200 LSB, no saturation, ~2000 pkt/s).
- Point cloud columns: `[range_bin, doppler_bin, angle, snr, zone_flag]` (5 columns). SNR at index 3, zone_flag at index 4.
