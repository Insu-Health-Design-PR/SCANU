# Layer1 Sensor Hub - Testing V2 Guide

This folder is the **new testing baseline** for sensor validation, JSON capture, and video capture.

Old scripts in `software/layer1_sensor_hub/examples` are intentionally kept for comparison.

## Scripts in This Folder

### 1) `run_live_hub.py`
Purpose:
- Run a live loop using mmWave + Infineon + thermal from one command.

Key options:
- `--mmwave on|off`
- `--config <path/to/mmwave.cfg>`
- `--presence mock|ifx|off`
- `--thermal on|off`
- `--max-frames 0` for continuous mode

Example:
```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --config software/layer1_sensor_hub/testing/configs/mmwave_main.cfg \
  --presence mock --thermal on --max-frames 0 --interval-s 0.1
```

### 2) `sensor_approval_hub.py`
Purpose:
- Approve connectivity for each sensor with PASS/FAIL output.
- Works as a preflight check before capture runs.

Key options:
- `--cli-port`, `--data-port`
- `--thermal-device`
- `--ifx-uuid`
- `--skip-mmwave`, `--skip-thermal`, `--skip-infineon`

Example:
```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --thermal-device 0
```

### 3) `device_check_hub.py`
Purpose:
- List serial and video devices.
- Best-effort mmWave auto-detect.

Example:
```bash
python3 software/layer1_sensor_hub/testing/device_check_hub.py
```

### 4) `capture_mmwave_json.py`
Purpose:
- Capture parsed mmWave frames and write JSON output.

Key options:
- `--frames`
- `--output`
- `--cli-port`, `--data-port`
- `--config <path/to/mmwave.cfg>`
- `--skip-config`

Example:
```bash
python3 software/layer1_sensor_hub/testing/capture_mmwave_json.py \
  --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/mmwave_main.cfg \
  --frames 300 --output /tmp/mmwave_capture.json
```

### 5) `capture_thermal_video.py`
Purpose:
- Capture thermal stream to MP4 and optional snapshot PNG.

Key options:
- `--device`, `--width`, `--height`, `--fps`
- `--seconds`
- `--video`, `--snapshot`

Example:
```bash
python3 software/layer1_sensor_hub/testing/capture_thermal_video.py \
  --device 0 --seconds 20 --video /tmp/thermal.mp4 --snapshot /tmp/thermal.png
```

## Recommended Execution Order

1. Run `device_check_hub.py`
2. Add your mmWave `.cfg` under `testing/configs/`
3. Run `sensor_approval_hub.py`
4. Run `run_live_hub.py`
5. Run `capture_mmwave_json.py` and `capture_thermal_video.py` as needed

## Test Suite (no sensor hardware required)

```bash
python3 -m pytest -q \
  software/layer1_sensor_hub/testing/test_sensor_hub.py \
  software/layer1_sensor_hub/testing/test_run_live_hub.py
```
