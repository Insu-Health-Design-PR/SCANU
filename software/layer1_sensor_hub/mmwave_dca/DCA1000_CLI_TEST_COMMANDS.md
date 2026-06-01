# DCA1000 CLI Test Commands

Use this flow when the TI DCA1000 CLI writes `adc_data.bin` and SCANU only
processes the captured file.

## 1. Hardware connections

```text
Radar LVDS -> DCA1000EVM
Radar USB  -> Jetson
DCA1000 Ethernet -> Jetson Ethernet
Radar power -> radar power supply
DCA1000 power -> DCA1000 power supply
```

## 2. Jetson Ethernet setup

```bash
sudo ip addr add 192.168.33.30/24 dev eth0
sudo ip link set eth0 up
```

Typical DCA1000 network values:

```text
Jetson IP: 192.168.33.30
DCA1000 IP: 192.168.33.180
Config port: 4096
Data port: 4098
```

## 3. Find the radar CLI port

```bash
ls /dev/ttyACM*
ls /dev/ttyUSB*
```

Use the radar CLI/control port in the radar configuration step. Common examples:

```text
/dev/ttyACM0
/dev/ttyUSB0
```

## 4. Go to the SCANU project

```bash
cd /home/insu/Desktop/SCANU-dev_adrian
source software/.venv/bin/activate
```

## 5. DCA1000 CLI setup

If the TI installer is already in this folder:

```text
software/layer1_sensor_hub/mmwave_dca/mmwave_studio_02_01_01_00_win32.exe
```

run this on the Jetson/Linux machine:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/mmwave_dca/ti_cli
chmod +x setup_ti_cli.sh run_dca1000_cli.sh
./setup_ti_cli.sh
```

If `DCA1000EVM_CLI_Control` is found or compiled, copy it into:

```text
software/layer1_sensor_hub/mmwave_dca/ti_cli/
```

Then configure and arm the DCA1000:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/mmwave_dca/ti_cli
./run_dca1000_cli.sh
```

Leave this terminal ready while the DCA1000 records.

## 6. Start the radar with LVDS ADC enabled

Open a second terminal:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian
source software/.venv/bin/activate
```

Send the DCA1000 ADC capture config to the radar:

```bash
python3 - <<'PY'
from pathlib import Path
from software.layer1_sensor_hub.mmwave_dca.radar_cli import RadarCliConfig, configure_radar_from_file

cli_port = "/dev/ttyACM0"
cfg = Path("software/layer1_sensor_hub/examples/configs/dca1000_adc_capture.cfg")

responses = configure_radar_from_file(
    RadarCliConfig(port=cli_port),
    cfg,
    defer_sensor_start=False,
)

print(f"sent_commands={len(responses)}")
for response in responses[-3:]:
    print(response.strip())
PY
```

Change `cli_port` if your radar uses a different port.

## 7. Stop DCA1000 recording

Return to the DCA1000 CLI terminal:

```bash
./DCA1000EVM_CLI_Control stop_record configFile.json
```

Confirm the capture file exists. The exact path depends on `configFile.json`.

```bash
ls -lh captures/
ls -lh adc_data*.bin
```

## 8. Process adc_data.bin with SCANU

From the SCANU project:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian
source software/.venv/bin/activate
```

Example for the included config:

```bash
python3 -m software.layer1_sensor_hub.mmwave_dca.process_adc_file \
  --input captures/adc_data.bin \
  --frames 100 \
  --chirps 16 \
  --rx 4 \
  --samples 384 \
  --output captures/range_doppler.png
```

The values must match the radar `.cfg`:

```text
frames: frameCfg frame count
chirps: loops per frame times number of chirps used
rx: active RX antennas
samples: ADC samples from profileCfg
```

For `dca1000_adc_capture.cfg`:

```text
rx = 4
samples = 384
chirps = 16
frames = 100
```

## 9. Quick file-size check

Expected bytes:

```text
frames * chirps * rx * samples * 2 I/Q values * 2 bytes
```

For the included config:

```text
100 * 16 * 4 * 384 * 2 * 2 = 9,830,400 bytes
```

Check it:

```bash
ls -lh captures/adc_data.bin
wc -c captures/adc_data.bin
```

If the file is much smaller, the recording likely started late, stopped early,
or Ethernet packets were not arriving correctly.

## 10. Common fixes

If `adc_data.bin` is empty:

```text
1. Confirm Jetson IP is 192.168.33.30.
2. Confirm DCA1000 was armed before radar sensorStart.
3. Confirm the radar config has lvdsStreamCfg -1 0 1 0.
4. Confirm Ethernet cable is connected directly or through the right interface.
5. Check firewall/network manager if packets do not arrive.
```

If Python says the shape is wrong:

```text
1. Re-check frames, chirps, rx, and samples.
2. Confirm the capture file is complete.
3. Try --allow-truncate only if you intentionally captured extra data.
4. Try --iq-order iq if the Range-Doppler map looks incorrect.
```
