# Layer1 Sensor Hub Examples

## 1) Run all 3 sensors live (mmWave + mock Infineon + thermal)

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --presence mock \
  --thermal on \
  --max-frames 0 \
  --interval-s 0.1
```

## 2) Run mmWave only

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --presence off \
  --thermal off
```

## 3) Run with explicit mmWave serial ports

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --presence mock \
  --thermal on
```

## 4) Run with real Infineon LTR11

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --presence ifx \
  --thermal on
```

## 5) Run tests

```bash
python3 -m pytest -q software/layer1_sensor_hub/testing/test_sensor_hub.py software/layer1_sensor_hub/testing/test_run_live_hub.py
```
