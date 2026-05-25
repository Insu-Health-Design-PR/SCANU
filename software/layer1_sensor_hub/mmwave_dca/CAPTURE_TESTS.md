# DCA1000 Capture Tests — Results

## Summary

Three test captures with different durations were executed to verify DCA1000 functionality and characterize the data stream.

## Test Configuration

| Parameter | Value |
|---|---|
| Radar | IWR6843 |
| Radar config | `weapon_detection_dca1000.cfg` |
| DCA1000 config | `ti_cli/configFile.json` |
| Capture mode | ethernetStream |
| Radar port | `/dev/ttyUSB0` |
| Jetson IP | `192.168.33.30` |
| DCA1000 IP | `192.168.33.180` |
| Config port | `4096` |
| Data port | `4098` |

### Radar Parameters (weapon_detection_dca1000.cfg)

| Parameter | Value |
|---|---|
| profileCfg samples | 384 |
| profileCfg rate | 2000 kHz |
| Active RX | 4 |
| Chirps per frame | 3 profiles × 16 loops = 48 chirps total |
| frameCfg frames | 100 |
| frameCfg periodicity | 100ms |
| lvdsStreamCfg | enabled (lane=1, format=0) |
| dataFormatMode | 3 (complex 2x) |

## Results

### Comparison Table

| Capture | Duration | Packets | Size | Rate (pkt/s) | Rate (MB/s) |
|---|---|---|---|---|---|
| test_3s | 3s | 5,965 | 8.3 MB | 1,988 | 2.77 |
| test_5s | 5s | 10,024 | 14 MB | 2,005 | 2.79 |
| test_10s | 10s | 20,151 | 28 MB | 2,015 | 2.79 |

### Consistency

Results are highly consistent across all 3 captures:

- **Packet rate**: ~2,000 UDP packets per second (variation <1.4%)
- **Bytes per packet**: **1456 fixed** (exact measurement across all 3 runs)
- **Data rate**: ~2.79 MB/s sustained
- **Signal dynamics**: range ±4000 int16, mean ~0, std ~205 (noisy ADC, no saturation)

## Data Format

### UDP Packet Structure (port 4098)

```
┌─────────────────────────────────────────────┐
│ Header (10 bytes)                            │
│  - sequence_number (4B uint32 LE)            │
│  - byte_count (4B uint32 LE)                 │
│  - reserved (2B)                             │
├─────────────────────────────────────────────┤
│ ADC Data (~1456 bytes)                       │
│  = 728 int16 values                          │
└─────────────────────────────────────────────┘
```

### TI Interleaved Format (dataFormatMode=3)

For 4 receivers (RX0..RX3), each sample produces 8 int16 values:

```
Sample 0: I0, I1, I2, I3, Q0, Q1, Q2, Q3  (8 int16 = 16 bytes)
Sample 1: I0, I1, I2, I3, Q0, Q1, Q2, Q3
...
Sample N: ...
```

This is known as "TI format" (alternative "IQ format" would be I,Q,I,Q,...).

### Expected Dimensions

| Dimension | Value | Source |
|---|---|---|
| Samples per chirp | 384 | profileCfg |
| RX | 4 | channelCfg |
| Chirps per frame | 16 | numLoops (frameCfg) |
| Frames | 100 | numFrames (frameCfg) |
| **Total expected bytes** | **9,830,400** | 100 × 16 × 4 × 384 × 2 × 2 |

### UDP Packing

- 1456 bytes payload = 728 int16 per packet
- 728 / (4 RX × 2 I/Q) = 91 samples per packet
- 384 samples / 91 samples = ~4.22 packets per chirp (DCA1000 fragments across chirps)

## Capture Variations

### Duration Effect

| Duration | Complete frames | Packets | Note |
|---|---|---|---|
| 3s | 88 | 5,965 | Truncated file: 8.68M < 9.83M (100 frames) |
| 5s | 148 | 10,024 | File exceeds 100 frames → truncated to 100 |
| 10s | 298 | 20,151 | File exceeds 100 frames → truncated to 100 |

At 100ms per frame with 16 chirps × 384 samples × 4 RX:
- In 3 seconds → ~30 frames expected, but DCA captures until stopped
- `frameCfg numFrames=100` does not limit when using `sensorStart` after DCA1000
- Actual duration controlled by capture timeout (`--duration-s`)

### Signal Quality

```
          test_3s     test_5s     test_10s
Min:      -4076       -4083       -4114
Max:       3955        3974        4014
Mean:       0.8         0.9         1.0
Std:      204.7       203.7       209.9
```

- Background noise ~200 LSB (expected for 14-16 bit ADC with gain)
- No saturation (never reaches ±32768)
- Mean near 0 (minimal DC offset)
- Consistent signals across captures

## Issues Found and Solutions

### 1. DCA1000 not responding to UDP commands

**Root cause**: This board's DCA1000 firmware does not implement `SYSTEM_CONNECT` (0x09), and the library sent it first.

**Fix** in `dca1000_control.py`:
- Changed `connect_first=True` → `False`
- Bind socket to config port (4096) instead of ephemeral port (0)
- Validate response by footer (0xEEAA) instead of checking status bytes

### 2. Wrong path in shell script

**Root cause**: `run_jetson_native_capture.sh` calculated `SOFTWARE_DIR` as the project root, not `software/`.

**Workaround**: Pass absolute paths via environment variables or use PYTHONPATH.

### 3. `ModuleNotFoundError: No module named 'layer1_sensor_hub'`

**Root cause**: Python cannot find local modules without PYTHONPATH.

**Fix**: `export PYTHONPATH=/home/insu/Desktop/SCANU-dev_adrian/software:$PYTHONPATH`

## Generated Files

```
captures/
├── adc_data.bin          (14M)  Last capture via run_jetson_native_capture.sh
├── test_3s.bin           (8.3M) 3-second capture
├── test_5s.bin           (14M)  5-second capture
├── test_10s.bin          (28M)  10-second capture
├── test_5s_rd.png               Range-Doppler from test_5s
└── test_10s_rd.png              Range-Doppler from test_10s
```
