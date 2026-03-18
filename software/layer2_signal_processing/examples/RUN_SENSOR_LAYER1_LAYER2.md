# Run Sensor Through Layer 1 And Layer 2

This guide is for Jetson/Linux using a downloaded project folder or zip extract.

Project root example:

```bash
cd ~/Desktop/SCANU-dev_adrian
```

If your extracted folder contains another nested `SCANU` folder, enter that one instead:

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
```

## 1. Confirm you are in the project root

```bash
pwd
ls
```

You should see at least:

- `software`
- `README.md`
- `run_sensor_layer1_layer2.sh`

## 2. Find the serial ports

Quick check:

```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

More detailed check:

```bash
python3 software/layer1_radar/examples/list_ports.py
```

## 3. Easiest way to run it

The shell launcher is the simplest option:

```bash
./run_sensor_layer1_layer2.sh --full
```

That tries to autodetect the radar ports.

## 4. Run with manual ports if needed

Replace `/dev/ttyUSB0` and `/dev/ttyUSB1` with your real ports.

Summary output:

```bash
./run_sensor_layer1_layer2.sh --config-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --frames 20
```

Full Layer 2 output for each frame:

```bash
./run_sensor_layer1_layer2.sh --config-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --frames 5 --full
```

Verbose logging:

```bash
./run_sensor_layer1_layer2.sh --config-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --frames 5 --full -v
```

Use a specific radar config file:

```bash
./run_sensor_layer1_layer2.sh --config-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --config /ruta/a/tu_config.cfg --frames 5 --full
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
- Make sure you are in the project root before running the launcher
- Run Layer 1 only first:

```bash
python3 software/layer1_radar/examples/capture_frames.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 10
```
