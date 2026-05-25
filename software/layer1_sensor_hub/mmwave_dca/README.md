# mmWave + DCA1000 Raw ADC Module

This module is for TI IWR6843ISK/AWR1843BOOST raw ADC capture through:

```text
Radar LVDS -> DCA1000EVM -> Ethernet -> Jetson/PC -> adc_data.bin
Radar USB  -> Jetson/PC CLI port for sensor config/start/stop
```

The existing `layer1_sensor_hub.mmwave` package reads processed TLV frames over UART.
This package is different: it records raw ADC samples from the DCA1000 Ethernet stream.

## Jetson network setup

```bash
sudo ip addr add 192.168.33.30/24 dev eth0
sudo ip link set eth0 up
```

Typical DCA1000 values:

- PC/Jetson IP: `192.168.33.30`
- DCA1000 IP: `192.168.33.180`
- Config port: `4096`
- Data port: `4098`

## Run a capture

There are two clean ways to use this module.

### Option 1: Jetson-native control and UDP capture

Use this on Jetson `aarch64` when you do not want Windows/mmWave Studio:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software
CLI_PORT=/dev/ttyACM0 CONFIGURE_NET=1 ./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

See `README_JETSON_NATIVE.md` for the full wiring, network, and troubleshooting
flow.

### Option 2: Python receives UDP after external DCA1000 setup

First configure/start the DCA1000 board with mmWave Studio or TI's DCA1000 CLI,
but let Python receive UDP and write the file:

```bash
python3 -m software.layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port /dev/ttyACM0 \
  --config software/layer1_sensor_hub/testing/configs/dca1000_adc_capture.cfg \
  --output captures/adc_data.bin \
  --duration-s 5
```

The radar `.cfg` must enable LVDS streaming. If it does not, the DCA1000 will not
receive ADC samples even if Ethernet is configured correctly.

The runner sends the `.cfg` without `sensorStart`, opens the UDP recorder, and
then sends `sensorStart`. That order avoids the common empty-file problem where
the radar starts before the DCA1000 data socket is listening.

## Read the ADC file

```python
from software.layer1_sensor_hub.mmwave_dca import AdcCaptureShape, read_adc_data

shape = AdcCaptureShape(frames=100, chirps=128, rx=4, samples=256)
adc = read_adc_data("captures/adc_data.bin", shape, iq_order="ti")
print(adc.shape)  # [frames, chirps, rx, samples]
```

### Option 3: TI CLI writes adc_data.bin, Python only processes it

Use TI's DCA1000 CLI to configure and record the capture file. Then process the
result with:

```bash
python3 -m software.layer1_sensor_hub.mmwave_dca.process_adc_file \
  --input captures/adc_data.bin \
  --frames 100 \
  --chirps 16 \
  --rx 4 \
  --samples 384 \
  --output captures/range_doppler.png
```

The `frames`, `chirps`, `rx`, and `samples` values must match the radar `.cfg`
used for that capture.

## Important notes

- This recorder listens for DCA1000 UDP data packets and writes ADC payload bytes.
- `dca1000_control.py` provides a Jetson-native replacement for the basic DCA1000 control commands.
- Empty `.bin` usually means the DCA1000 was not armed, LVDS was not enabled, IP is wrong, or the radar started before recording.
- For the TI CLI workflow where the CLI writes `adc_data.bin`, use `DCA1000_CLI_TEST_COMMANDS.md`.
- The TI CLI helper files live in `ti_cli/`.
