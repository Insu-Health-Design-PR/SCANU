# Layer 6 - Command Guide (Jetson)

This guide provides operational commands for Layer 6 state + control plane.

## 1) Environment Setup

```bash
cd ~/SCANU
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r software/layer1_radar/requirements.txt
```

## 2) Smoke Test (No Hardware)

Run Layer 6 in simulation mode first:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main run --mode simulate --max-frames 5
```

Expected: JSON output with `event`, `snapshot`, and optionally `action_request`.

## 3) Radar Status

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main status
```

## 4) Apply Radar Configuration

Using known ports:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --config software/layer1_sensor_hub/testing/configs/full_config.cfg \
  reconfig
```

## 5) Run Live Layer 6

mmWave on, mock presence, thermal off:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  run --mode live --mmwave on --presence mock --thermal off --max-frames 50
```

Long-run mode:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  run --mode live --mmwave on --presence mock --thermal off --max-frames 0
```

## 6) Soft Recovery (Safe Automatic Path)

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  reset
```

## 7) Manual Destructive Actions

`kill` requires explicit confirmation:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  kill --force --confirm-manual
```

`usb-reset` requires explicit confirmation:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  usb-reset --confirm-manual
```

## 8) Multi-Radar (Primary + Optional Aux)

Add auxiliary radars with:

```bash
--aux-radar radar_aux_1:/dev/ttyUSB2:/dev/ttyUSB3:/path/to/config.cfg
```

Example:

```bash
PYTHONPATH=. python3 -m software.layer6_state_machine.run_layer6 \
  --radar-id radar_main \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --aux-radar radar_aux_1:/dev/ttyUSB2:/dev/ttyUSB3:software/layer1_sensor_hub/testing/configs/full_config.cfg \
  status
```

## 9) Typical Flow on Jetson

1. Run simulation smoke test.
2. Check status.
3. Reconfigure radar.
4. Run live loop.
5. If radar stalls, use `reset` first.
6. Use `kill` or `usb-reset` only as manual last resort.

## 10) Notes

- `radar_main` is required.
- `radar_aux_*` are optional.
- Layer 6 currently uses provisional L1/L2 input adapter (`source_mode=provisional_l1_l2`).
- When Layer 5 output is available, only adapter wiring needs replacement.
