# Infineon 60GHz Testing Guide

## Scope

This guide validates the Infineon 60GHz presence sensor path only (no mmWave, no thermal).

## 1) Preconditions

```bash
cd /home/insu/Desktop/SCANU-dev_adrian
python3 -c "import ifxradarsdk; print('ifxradarsdk OK')"
```

Expected: `ifxradarsdk OK`

## 2) Connectivity Check (Infineon only)

```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --skip-mmwave \
  --skip-thermal
```

Optional UUID:

```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --skip-mmwave \
  --skip-thermal \
  --ifx-uuid <REAL_UUID>
```

Notes:
- Do not include `< >` in shell for real UUID usage.
- This check validates connectivity/read path, not full detection quality.

## 3) Live Loop (Infineon only)

```bash
python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave off \
  --thermal off \
  --presence ifx \
  --max-frames 100 \
  --interval-s 0.2
```

Expected output shape:

```text
frame=N | mmw=off | ifx=on presence=0.xxx motion=0.xxx dist=N/A | thermal=off
```

## 3.1) Basic person-pass detector (value + zone + detection time)

Run:

```bash
python3 software/layer1_sensor_hub/testing/ifx_presence_basic.py \
  --duration-s 30 \
  --interval-s 0.2 \
  --presence-th 0.45 \
  --motion-th 0.35
```

Optional UUID:

```bash
python3 software/layer1_sensor_hub/testing/ifx_presence_basic.py \
  --ifx-uuid <REAL_UUID> \
  --duration-s 30 \
  --interval-s 0.2
```

What it prints:
- Live signal value (`presence`, `motion`)
- Basic location proxy (`zone=near|mid|far`)
- Detection timeline (`start`, `end`, `duration`)

What it saves:
- JSON event list in `software/layer1_sensor_hub/testing/view/ifx_events_<timestamp>.json`

## 4) Raw Metadata Diagnostic

Use this when output seems weak/intermittent:

```bash
python3 - <<'PY'
import time
from software.layer1_sensor_hub.infeneon import IfxLtr11PresenceProvider

p = IfxLtr11PresenceProvider()
try:
    for i in range(80):
        presence, motion, _dist = p.read_sample()
        meta = p.last_meta or {}
        print(
            f"{i:03d} presence={presence:.3f} motion={motion:.3f} "
            f"active={meta.get('active')} motion_flag={meta.get('motion')} "
            f"avg_power={meta.get('avg_power', 0):.6f}"
        )
        time.sleep(0.15)
finally:
    p.close()
PY
```

Interpretation:
- `active=True` during person presence is a strong positive signal.
- `motion` may stay low if subject is mostly static.
- `dist=N/A` is expected in this path because direct distance is not exposed here.

## 5) Current Code Behavior (Analysis)

- `presence_raw` is computed from a combined signal (`active + power + motion`) with smoothing in:
  - `software/layer1_sensor_hub/infeneon/ifx_ltr11_provider.py`
- `motion_raw` is a hybrid of motion flag and normalized motion energy.
- `distance_m` is intentionally not treated as real distance in this flow.

## 6) Current Test Coverage (Analysis)

Existing tests in `software/layer1_sensor_hub/testing/` are mostly integration-light and mock-based:
- `test_run_live_hub.py`
- `test_sensor_hub.py`
- `test_testing_scripts.py`

Gaps for the 60GHz sensor:
- No hardware-backed regression test for `IfxLtr11PresenceProvider`.
- No threshold/acceptance test for static-person presence quality.
- No long-run stability test (disconnect/reconnect behavior).

## 7) Suggested Acceptance Targets

- Empty scene: presence low and stable, no persistent motion.
- Person crossing FOV: clear rise in presence/motion within 1-2 seconds.
- Person standing: presence remains elevated even if motion decreases.






