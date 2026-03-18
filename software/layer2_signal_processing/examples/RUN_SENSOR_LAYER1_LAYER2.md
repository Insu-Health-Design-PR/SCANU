# Run Sensor Through Layer 1 And Layer 2

This guide is for Jetson/Linux. The commands below are ready to copy and paste.

## 1. Go to the repo

```bash
cd /ruta/a/SCANU
```

## 2. Update your branch

For `dev_adrian`:

```bash
git checkout dev_adrian
git pull origin dev_adrian
```

For `main`:

```bash
git checkout main
git pull origin main
```

## 3. Find the serial ports

Quick check:

```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

More detailed check:

```bash
python3 software/layer1_radar/examples/list_ports.py
```

## 4. Run the live sensor through Layer 1 and Layer 2

Replace `/dev/ttyUSB0` and `/dev/ttyUSB1` with your real ports.

Summary output:

```bash
python3 software/layer2_signal_processing/examples/run_sensor_layer1_layer2.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 20
```

Full Layer 2 output for each frame:

```bash
python3 software/layer2_signal_processing/examples/run_sensor_layer1_layer2.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 5 \
  --full
```

Verbose logging:

```bash
python3 software/layer2_signal_processing/examples/run_sensor_layer1_layer2.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 5 \
  --full \
  -v
```

Use a specific radar config file:

```bash
python3 software/layer2_signal_processing/examples/run_sensor_layer1_layer2.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config /ruta/a/tu_config.cfg \
  --frames 5 \
  --full
```

## 5. What you should see

The script connects the radar, reads live data in Layer 1, processes it in Layer 2, and prints:

- `ProcessedFrame`
  - `frame_number`
  - `timestamp_ms`
  - `source_timestamp_cycles`
  - `range_doppler`
  - `point_cloud`
- `HeatmapFeatures`
  - `range_heatmap`
  - `doppler_heatmap`
  - `vector`

## 6. If it fails

Try these checks:

- Swap `--config-port` and `--data-port`
- Confirm the radar is powered and detected by Linux
- Run Layer 1 only first:

```bash
python3 software/layer1_radar/examples/capture_frames.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 10
```
