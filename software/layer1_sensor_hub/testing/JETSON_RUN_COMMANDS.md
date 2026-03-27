# Jetson Commands (Testing V2)

## 1) Move to repository root

Default workspace used in these commands:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian
```

Quick path check:

```bash
ls software/layer1_sensor_hub/testing/capture_all_sensors.py
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

## 4) Sensor approval test (PASS/FAIL)

```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --thermal-device 0
```

## 5) Run all sensors live

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --presence ifx \
  --thermal on \
  --thermal-device 0 \
  --max-frames 0 \
  --interval-s 0.1
```

## 6) Capture mmWave JSON

```bash
python3 software/layer1_sensor_hub/testing/capture_mmwave_json.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/mmwave_capture.json
```

## 7) Capture thermal MP4 + snapshot

```bash
python3 software/layer1_sensor_hub/testing/capture_thermal_video.py \
  --device 0 \
  --seconds 20 \
  --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/thermal_capture.mp4 \
  --snapshot /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/thermal_snapshot.png
```

## 8) Capture all sensors in one command (video + json)

```bash
python3 software/layer1_sensor_hub/testing/capture_all_sensors.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/all_sensors.mp4 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/all_sensors.json \
  --thermal-device 0 \
  --presence ifx
```

## 9) Run mmWave only (principal sensor tuned)

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --presence off \
  --thermal off \
  --max-frames 0 \
  --interval-s 0.1 \
  --mmw-min-snr-db 5 \
  --mmw-max-azimuth-deg 60 \
  --mmw-max-range-m 6
```

## 10) Run unit tests

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  software/layer1_sensor_hub/testing/test_sensor_hub.py \
  software/layer1_sensor_hub/testing/test_run_live_hub.py \
  software/layer1_sensor_hub/testing/test_testing_scripts.py
```
