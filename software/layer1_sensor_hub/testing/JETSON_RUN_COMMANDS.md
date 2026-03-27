# Jetson Commands (Copy/Paste)

## 1) Go to project root

Use the path you confirmed on Jetson.

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
```

If your Jetson repo is without the `SCANU` subfolder, use:

```bash
cd ~/Desktop/SCANU-dev_adrian
```

## 2) Optional: install runtime deps

```bash
python3 -m pip install -U pyserial numpy opencv-python
```

For real Infineon hardware provider (`--presence ifx`), also install your `ifxradarsdk`.

## 3) Run 3 sensors live (safe default: mock Infineon)

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --presence mock \
  --thermal on \
  --max-frames 0 \
  --interval-s 0.1
```

## 4) Run with explicit mmWave ports

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --presence mock \
  --thermal on
```

## 5) Run with real Infineon LTR11

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave on \
  --presence ifx \
  --thermal on
```

## 6) Quick smoke tests (no hardware needed)

```bash
python3 -m pytest -q software/layer1_sensor_hub/testing/test_sensor_hub.py software/layer1_sensor_hub/testing/test_run_live_hub.py
```

