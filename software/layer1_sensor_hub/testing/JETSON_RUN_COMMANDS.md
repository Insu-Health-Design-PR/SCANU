# Jetson Commands (Testing V2)

## 1) Move to repository root

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
```

## 2) Install runtime dependencies

```bash
python3 -m pip install -U pyserial numpy opencv-python matplotlib
```

Optional for real Infineon SDK mode:

```bash
python3 -m pip install ifxradarsdk
```

## 3) Device visibility check

```bash
python3 software/layer1_sensor_hub/testing/device_check_hub.py
```

## 4) Add mmWave config file

Put your config file here:

```bash
software/layer1_sensor_hub/testing/configs/mmwave_main.cfg
```

## 5) Sensor approval test (PASS/FAIL)

```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --thermal-device 0
```

## 6) Run all sensors live

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --config software/layer1_sensor_hub/testing/configs/mmwave_main.cfg \
  --presence mock \
  --thermal on \
  --max-frames 0 \
  --interval-s 0.1
```

## 7) Capture mmWave JSON

```bash
python3 software/layer1_sensor_hub/testing/capture_mmwave_json.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/mmwave_main.cfg \
  --frames 300 \
  --output /tmp/mmwave_capture.json
```

## 8) Capture thermal MP4 + snapshot

```bash
python3 software/layer1_sensor_hub/testing/capture_thermal_video.py \
  --device 0 \
  --seconds 20 \
  --video /tmp/thermal_capture.mp4 \
  --snapshot /tmp/thermal_snapshot.png
```

## 9) Run unit tests

```bash
python3 -m pytest -q \
  software/layer1_sensor_hub/testing/test_sensor_hub.py \
  software/layer1_sensor_hub/testing/test_run_live_hub.py
```
