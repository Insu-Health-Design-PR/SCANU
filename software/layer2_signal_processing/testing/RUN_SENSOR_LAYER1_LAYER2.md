# Run Live Sensor Through Layer 1 And Layer 2

This guide is for Jetson/Linux when you received the project as a zip, extracted it locally, and want to test a physical radar sensor through:

`Sensor -> Layer 1 -> Layer 2`

The development runner for this flow is:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py
```

It calls:

```bash
software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py
```

## 1. Enter the correct project root

Example:

```bash
cd ~/Desktop/SCANU-dev_adrian/SCANU
```

If you are not sure which folder is the real root, validate with:

```bash
pwd
ls
```

You should see at least:

```bash
software
README.md
```

If `software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py` is missing, you are probably one folder above or below the real root.

## 2. Quick port check in Linux

Before trying to start the sensor, check which serial devices are visible:

```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

If nothing appears, the radar may not be visible yet to Linux.

For a more detailed inspection, run:

```bash
python3 software/layer1_radar/examples/list_ports.py
```

That is useful to confirm which port looks like the config/CLI port and which one looks like the data port.

## 3. Recommended first command

Start with:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --check
```

What `--check` does:

- validates your arguments
- prints the runtime plan
- prints visible `/dev/ttyUSB*` and `/dev/ttyACM*` devices from the shell launcher
- does **not** start the sensor
- exits with code `0` if the runner configuration looks valid

This is the safest first step on Jetson before attempting live capture.

## 4. Accepted port flag names

The Python runner accepts these names:

- `--config-port`
- `--cli-port` as a friendly alias of `--config-port`
- `--data-port`

If you provide ports manually, you must provide both the config/CLI port and the data port.

## 5. Common execution examples

Autodetect ports, summary output:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --frames 20
```

Autodetect ports, full JSON output:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --frames 5 --full
```

Manual ports, summary output:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 20
```

Manual ports using the `--cli-port` alias:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 20
```

Manual ports, verbose logging:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 10 \
  --verbose
```

Manual ports, full JSON output:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 5 \
  --full
```

Custom radar config file:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_radar/examples/configs/full_config.cfg \
  --frames 5 \
  --full
```

## 6. What the runner prints

Before starting live capture, the runner prints:

- `LIVE SENSOR -> LAYER 1 -> LAYER 2`
- a runtime plan
- port mode: `manual` or `autodetect`
- config source: default or custom file
- frame count
- output mode: `summary` or `full JSON`
- verbose logging: `yes` or `no`

During live execution:

- summary mode prints one compact line per frame
- full mode prints full Layer 2 JSON for each frame

This lets you confirm that real sensor data is reaching Layer 2.

## 7. Save logs with tee

To save the output while still seeing it live:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 10 \
  --full \
  --verbose | tee layer1_layer2_live.log
```

## 8. Common errors

### Only one port was provided

Incorrect:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --cli-port /dev/ttyUSB0 --frames 10
```

Why it fails:

- manual port mode requires both config/CLI port and data port

Correct:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --cli-port /dev/ttyUSB0 --data-port /dev/ttyUSB1 --frames 10
```

### Config file does not exist

Incorrect:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --config /tmp/missing.cfg --frames 5
```

Why it fails:

- the runner validates that the file exists before attempting live execution

### Mixing examples from other scripts

Be careful not to mix flags copied from other commands or documents that use different runner names.

For this runner, keep the command shape consistent with:

```bash
python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py [--config-port|--cli-port <port>] [--data-port <port>] [--config <file>] [--frames N] [--full] [-v]
```

## 9. Troubleshooting checklist

Use this checklist if the sensor does not start or Layer 2 output does not appear:

- Confirm you are in the correct project root.
- Run `python3 software/layer2_signal_processing/testing/run_sensor_layer1_layer2.py --check` first.
- Run `ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null` and verify the radar appears.
- Run `python3 software/layer1_radar/examples/list_ports.py` for more detail.
- Verify that config/CLI and data ports are not swapped.
- Re-run with `-v` or `--verbose`.
- If needed, try the default config first before testing a custom config file.
- If Layer 2 still does not print frames, test Layer 1 capture by itself:

```bash
python3 software/layer1_radar/examples/capture_frames.py \
  --config-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --frames 10
```

If Layer 1 alone cannot capture frames, fix that first before debugging Layer 2.
