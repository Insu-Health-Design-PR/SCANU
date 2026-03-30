# Jetson Commands (Testing V2)

## 1) Move to repository root

If your project has `.../SCANU` as subfolder:

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
```

If your project root is directly `.../SCANU-dev_adrian`:

```bash
cd ~/Desktop/SCANU-dev_adrian
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

## 4) Add mmWave config file

Put your config file here:

`  --mmwave on \
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
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/testq.json
```

## 8) Capture thermal MP4 + snapshot

```bash
python3 software/layer1_sensor_hub/testing/capture_thermal_video.py \
  --device 0 \
  --seconds 20 \
  --video /tmp/thermal_capture.mp4 \
  --snapshot /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/view/thermal_snapshot.png
```

## 9) Run unit tests

```bash
python3 -m pytest -q \
  software/layer1_sensor_hub/testing/test_sensor_hub.py \
  software/layer1_sensor_hub/testing/test_run_live_hub.py
```

## 10) Capture all sensors in one command (video + json)

```bash
python3 software/layer1_sensor_hub/testing/capture_all_sensors.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/all_sensors.mp4 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/all_sensors.json \
  --thermal-device 0 \
  --presence ifx``bash
software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg
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
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
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
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test1.json
```

## 8) Capture thermal MP4 + snapshot

```bash
python3 software/layer1_sensor_hub/testing/capture_thermal_video.py \
  --device 0 \
  --seconds 20 \
  --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/thermal_capture.mp4 \
  --snapshot /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view//thermal_snapshot.png
```

## 9) Run unit tests

```bash
python3 -m pytest -q \
  software/layer1_sensor_hub/testing/test_sensor_hub.py \
  software/layer1_sensor_hub/testing/test_run_live_hub.py
```

## 10) Capture all sensors in one command (video + json)

```bash
python3 software/layer1_sensor_hub/testing/capture_all_sensors.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test2.mp4 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test2.json \
  --thermal-device 0 \
  --presence ifx
```

## 11) Quick serial checks + capture command (single line)

```bash
cd /home/insu/Desktop/SCANU-dev_adrian
ls -l /dev/ttyUSB*
lsof /dev/ttyUSB0 /dev/ttyUSB1
sudo fuser -k /dev/ttyUSB0 /dev/ttyUSB1
```

```bash
python3 software/layer1_sensor_hub/testing/capture_all_sensors.py --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg --frames 300 --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test2.mp4 --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test2.json --thermal-device 0 --presence ifx
```

## 12) Clean stale processes/ports + run capture (stable config)

```bash
cd /home/insu/Desktop/SCANU-dev_adrian && \
pkill -f capture_all_sensors.py || true && \
pkill -f run_live_hub.py || true && \
sudo fuser -k /dev/ttyUSB0 /dev/ttyUSB1 2>/dev/null || true && \
sleep 1 && \
python3 software/layer1_sensor_hub/testing/capture_all_sensors.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --frames 300 \
  --video /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test2.mp4 \
  --output /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/view/test2.json \
  --thermal-device 0 \
  --presence ifx
```
