# Jetson Native DCA1000 Capture

Use this path when the capture machine is a Jetson (`aarch64`) and you do not
want a Windows laptop or TI's `DCA1000EVM_CLI_Control.exe`.

```text
Radar USB/UART  -> Jetson       sends radar .cfg and sensorStart
Radar LVDS      -> DCA1000EVM   raw ADC stream
DCA1000 Ethernet -> Jetson      UDP control + UDP ADC packets
```

## 1. Physical connections

- Radar USB/control port to Jetson USB.
- Radar LVDS connector to DCA1000EVM LVDS connector.
- DCA1000EVM Ethernet directly to Jetson Ethernet.
- Power the radar board and DCA1000EVM as required by TI.

## 2. Jetson network

The DCA1000 default network is normally:

- Jetson/PC IP: `192.168.33.30`
- DCA1000 IP: `192.168.33.180`
- Config UDP port: `4096`
- Data UDP port: `4098`

Run once after connecting Ethernet:

```bash
sudo ip addr flush dev eth0
sudo ip addr add 192.168.33.30/24 dev eth0
sudo ip link set eth0 up
ping 192.168.33.180
```

If your Jetson Ethernet device is not `eth0`, find it:

```bash
ip link
```

## 3. One-command capture

From the repo:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

CLI_PORT=/dev/ttyACM0 \
ETH_DEV=eth0 \
CONFIGURE_NET=1 \
DURATION_S=5 \
./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

Output defaults to:

```text
software/captures/adc_data.bin
```

## 4. Manual command flow

Configure DCA1000 over UDP:

```bash
python3 -m layer1_sensor_hub.mmwave_dca.dca1000_control configure \
  --config layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json
```

Configure radar, arm DCA1000, start radar, receive UDP ADC, stop:

```bash
python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port /dev/ttyACM0 \
  --config layer1_sensor_hub/testing/configs/dca1000_adc_capture.cfg \
  --dca-config layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
  --output captures/adc_data.bin \
  --duration-s 5 \
  --configure-dca \
  --start-dca \
  --stop-dca
```

## 5. If DCA1000 commands fail

The native controller sends the public DCA1000 UDP command frame:

```text
0xA55A header + command + payload length + payload + 0xEEAA footer
```

TI firmware/CLI releases can differ in exact FPGA/packet payload bytes. If
`connect` works but `fpga` or `packet` fails, put the exact hex payload in:

```json
"nativeCommandPayloads": {
  "fpga": "01 02 01 02 03",
  "packet": "19 00"
}
```

inside:

```text
layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json
```

## 6. Troubleshooting

- `ping 192.168.33.180` fails: Ethernet IP or cable is wrong.
- `Address already in use`: another process is listening on UDP `4098`.
- Empty `adc_data.bin`: radar LVDS is not enabled, DCA1000 did not start, or
  radar started before data capture was armed.
- `No such file /dev/ttyACM0`: check the radar CLI port with `ls /dev/ttyACM* /dev/ttyUSB*`.
- Permission denied on serial: add user to `dialout`, then log out/in:

```bash
sudo usermod -aG dialout $USER
```
