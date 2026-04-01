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










insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ cd /home/insu/Desktop/SCANU-dev_adrian
python3 -c "import ifxradarsdk; print('ifxradarsdk OK')"
ifxradarsdk OK
insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --skip-mmwave \
  --skip-thermal

Sensor approval results
============================================================
[PASS] mmWave: skipped
[PASS] Thermal: skipped
[PASS] Infineon: SDK ok: presence_raw=0.150000 motion_raw=1.0
============================================================
Elapsed: 0.89s


insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ python3 software/layer1_sensor_hub/testing/run_live_hub.py \
  --mmwave off \
  --thermal off \
  --presence ifx \
  --max-frames 100 \
  --interval-s 0.2
Starting live sensor loop. Press Ctrl+C to stop.
frame=1 | mmw=off | ifx=on presence=0.150 motion=1.000 dist=N/A | thermal=off
frame=2 | mmw=off | ifx=on presence=0.265 motion=1.000 dist=N/A | thermal=off
frame=3 | mmw=off | ifx=on presence=0.350 motion=0.027 dist=N/A | thermal=off
frame=4 | mmw=off | ifx=on presence=0.413 motion=0.031 dist=N/A | thermal=off
frame=5 | mmw=off | ifx=on presence=0.460 motion=0.019 dist=N/A | thermal=off
frame=6 | mmw=off | ifx=on presence=0.496 motion=0.017 dist=N/A | thermal=off
frame=7 | mmw=off | ifx=on presence=0.522 motion=0.016 dist=N/A | thermal=off
frame=8 | mmw=off | ifx=on presence=0.542 motion=0.018 dist=N/A | thermal=off
frame=9 | mmw=off | ifx=on presence=0.557 motion=0.015 dist=N/A | thermal=off
frame=10 | mmw=off | ifx=on presence=0.568 motion=0.020 dist=N/A | thermal=off
frame=11 | mmw=off | ifx=on presence=0.576 motion=0.014 dist=N/A | thermal=off
frame=12 | mmw=off | ifx=on presence=0.583 motion=0.019 dist=N/A | thermal=off
frame=13 | mmw=off | ifx=on presence=0.587 motion=0.014 dist=N/A | thermal=off
frame=14 | mmw=off | ifx=on presence=0.591 motion=1.000 dist=N/A | thermal=off
frame=15 | mmw=off | ifx=on presence=0.594 motion=1.000 dist=N/A | thermal=off
frame=16 | mmw=off | ifx=on presence=0.596 motion=1.000 dist=N/A | thermal=off
frame=17 | mmw=off | ifx=on presence=0.597 motion=1.000 dist=N/A | thermal=off
frame=18 | mmw=off | ifx=on presence=0.598 motion=1.000 dist=N/A | thermal=off
frame=19 | mmw=off | ifx=on presence=0.599 motion=1.000 dist=N/A | thermal=off
frame=20 | mmw=off | ifx=on presence=0.600 motion=0.021 dist=N/A | thermal=off
frame=21 | mmw=off | ifx=on presence=0.601 motion=0.020 dist=N/A | thermal=off
frame=22 | mmw=off | ifx=on presence=0.601 motion=0.015 dist=N/A | thermal=off
frame=23 | mmw=off | ifx=on presence=0.601 motion=0.019 dist=N/A | thermal=off
frame=24 | mmw=off | ifx=on presence=0.601 motion=0.026 dist=N/A | thermal=off
frame=25 | mmw=off | ifx=on presence=0.602 motion=0.029 dist=N/A | thermal=off
frame=26 | mmw=off | ifx=on presence=0.602 motion=0.032 dist=N/A | thermal=off
frame=27 | mmw=off | ifx=on presence=0.603 motion=0.066 dist=N/A | thermal=off
frame=28 | mmw=off | ifx=on presence=0.607 motion=0.177 dist=N/A | thermal=off
frame=29 | mmw=off | ifx=on presence=0.614 motion=0.358 dist=N/A | thermal=off
frame=30 | mmw=off | ifx=on presence=0.625 motion=0.593 dist=N/A | thermal=off
frame=31 | mmw=off | ifx=on presence=0.636 motion=0.689 dist=N/A | thermal=off
frame=32 | mmw=off | ifx=on presence=0.644 motion=0.658 dist=N/A | thermal=off
frame=33 | mmw=off | ifx=on presence=0.644 motion=0.470 dist=N/A | thermal=off
frame=34 | mmw=off | ifx=on presence=0.640 motion=0.272 dist=N/A | thermal=off
frame=35 | mmw=off | ifx=on presence=0.635 motion=0.196 dist=N/A | thermal=off
frame=36 | mmw=off | ifx=on presence=0.634 motion=0.290 dist=N/A | thermal=off
frame=37 | mmw=off | ifx=on presence=0.636 motion=0.431 dist=N/A | thermal=off
frame=38 | mmw=off | ifx=on presence=0.640 motion=0.516 dist=N/A | thermal=off
frame=39 | mmw=off | ifx=on presence=0.643 motion=0.544 dist=N/A | thermal=off
frame=40 | mmw=off | ifx=on presence=0.650 motion=0.703 dist=N/A | thermal=off
frame=41 | mmw=off | ifx=on presence=0.654 motion=0.639 dist=N/A | thermal=off
frame=42 | mmw=off | ifx=on presence=0.656 motion=0.624 dist=N/A | thermal=off
frame=43 | mmw=off | ifx=on presence=0.657 motion=0.600 dist=N/A | thermal=off
frame=44 | mmw=off | ifx=on presence=0.658 motion=0.607 dist=N/A | thermal=off
frame=45 | mmw=off | ifx=on presence=0.657 motion=0.528 dist=N/A | thermal=off
frame=46 | mmw=off | ifx=on presence=0.662 motion=0.783 dist=N/A | thermal=off
frame=47 | mmw=off | ifx=on presence=0.664 motion=0.710 dist=N/A | thermal=off
frame=48 | mmw=off | ifx=on presence=0.663 motion=0.573 dist=N/A | thermal=off
frame=49 | mmw=off | ifx=on presence=0.658 motion=0.450 dist=N/A | thermal=off
frame=50 | mmw=off | ifx=on presence=0.648 motion=0.190 dist=N/A | thermal=off
frame=51 | mmw=off | ifx=on presence=0.640 motion=0.141 dist=N/A | thermal=off
frame=52 | mmw=off | ifx=on presence=0.635 motion=0.199 dist=N/A | thermal=off
frame=53 | mmw=off | ifx=on presence=0.638 motion=0.460 dist=N/A | thermal=off
frame=54 | mmw=off | ifx=on presence=0.642 motion=0.563 dist=N/A | thermal=off
frame=55 | mmw=off | ifx=on presence=0.646 motion=0.556 dist=N/A | thermal=off
frame=56 | mmw=off | ifx=on presence=0.649 motion=0.590 dist=N/A | thermal=off
frame=57 | mmw=off | ifx=on presence=0.651 motion=0.554 dist=N/A | thermal=off
frame=58 | mmw=off | ifx=on presence=0.650 motion=0.472 dist=N/A | thermal=off
frame=59 | mmw=off | ifx=on presence=0.645 motion=0.296 dist=N/A | thermal=off
frame=60 | mmw=off | ifx=on presence=0.639 motion=0.223 dist=N/A | thermal=off
frame=61 | mmw=off | ifx=on presence=0.636 motion=0.251 dist=N/A | thermal=off
frame=62 | mmw=off | ifx=on presence=0.636 motion=0.360 dist=N/A | thermal=off
frame=63 | mmw=off | ifx=on presence=0.640 motion=0.514 dist=N/A | thermal=off
frame=64 | mmw=off | ifx=on presence=0.648 motion=0.748 dist=N/A | thermal=off
frame=65 | mmw=off | ifx=on presence=0.654 motion=0.710 dist=N/A | thermal=off
frame=66 | mmw=off | ifx=on presence=0.659 motion=0.725 dist=N/A | thermal=off
frame=67 | mmw=off | ifx=on presence=0.657 motion=0.533 dist=N/A | thermal=off
frame=68 | mmw=off | ifx=on presence=0.650 motion=0.274 dist=N/A | thermal=off
frame=69 | mmw=off | ifx=on presence=0.642 motion=0.196 dist=N/A | thermal=off
frame=70 | mmw=off | ifx=on presence=0.637 motion=0.226 dist=N/A | thermal=off
frame=71 | mmw=off | ifx=on presence=0.638 motion=0.403 dist=N/A | thermal=off
frame=72 | mmw=off | ifx=on presence=0.639 motion=0.421 dist=N/A | thermal=off
frame=73 | mmw=off | ifx=on presence=0.641 motion=0.483 dist=N/A | thermal=off
frame=74 | mmw=off | ifx=on presence=0.649 motion=0.719 dist=N/A | thermal=off
frame=75 | mmw=off | ifx=on presence=0.653 motion=0.661 dist=N/A | thermal=off
frame=76 | mmw=off | ifx=on presence=0.651 motion=0.435 dist=N/A | thermal=off
frame=77 | mmw=off | ifx=on presence=0.646 motion=0.308 dist=N/A | thermal=off
frame=78 | mmw=off | ifx=on presence=0.642 motion=0.294 dist=N/A | thermal=off
frame=79 | mmw=off | ifx=on presence=0.642 motion=0.435 dist=N/A | thermal=off
frame=80 | mmw=off | ifx=on presence=0.647 motion=0.615 dist=N/A | thermal=off
frame=81 | mmw=off | ifx=on presence=0.653 motion=0.699 dist=N/A | thermal=off
frame=82 | mmw=off | ifx=on presence=0.656 motion=0.667 dist=N/A | thermal=off
frame=83 | mmw=off | ifx=on presence=0.658 motion=0.618 dist=N/A | thermal=off
frame=84 | mmw=off | ifx=on presence=0.656 motion=0.530 dist=N/A | thermal=off
frame=85 | mmw=off | ifx=on presence=0.648 motion=0.241 dist=N/A | thermal=off
frame=86 | mmw=off | ifx=on presence=0.641 motion=0.179 dist=N/A | thermal=off
frame=87 | mmw=off | ifx=on presence=0.636 motion=0.198 dist=N/A | thermal=off
frame=88 | mmw=off | ifx=on presence=0.635 motion=0.333 dist=N/A | thermal=off
frame=89 | mmw=off | ifx=on presence=0.639 motion=0.502 dist=N/A | thermal=off
frame=90 | mmw=off | ifx=on presence=0.642 motion=0.507 dist=N/A | thermal=off
frame=91 | mmw=off | ifx=on presence=0.646 motion=0.571 dist=N/A | thermal=off
frame=92 | mmw=off | ifx=on presence=0.650 motion=0.617 dist=N/A | thermal=off
frame=93 | mmw=off | ifx=on presence=0.650 motion=0.506 dist=N/A | thermal=off
frame=94 | mmw=off | ifx=on presence=0.645 motion=0.311 dist=N/A | thermal=off
frame=95 | mmw=off | ifx=on presence=0.642 motion=0.306 dist=N/A | thermal=off
frame=96 | mmw=off | ifx=on presence=0.640 motion=0.348 dist=N/A | thermal=off
frame=97 | mmw=off | ifx=on presence=0.642 motion=0.481 dist=N/A | thermal=off
frame=98 | mmw=off | ifx=on presence=0.649 motion=0.714 dist=N/A | thermal=off
frame=99 | mmw=off | ifx=on presence=0.653 motion=0.650 dist=N/A | thermal=off
frame=100 | mmw=off | ifx=on presence=0.650 motion=0.406 dist=N/A | thermal=off


insu@insu-desktop:~/Desktop/SCANU-dev_adrian$ python3 - <<'PY'
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
000 presence=0.150 motion=1.000 active=True motion_flag=True avg_power=0.005664
001 presence=0.265 motion=1.000 active=True motion_flag=True avg_power=0.005664
002 presence=0.349 motion=0.022 active=True motion_flag=False avg_power=0.005664
003 presence=0.413 motion=0.017 active=True motion_flag=False avg_power=0.005664
004 presence=0.460 motion=0.018 active=True motion_flag=False avg_power=0.005664
005 presence=0.495 motion=0.013 active=True motion_flag=False avg_power=0.005664
006 presence=0.522 motion=0.016 active=True motion_flag=False avg_power=0.005664
007 presence=0.542 motion=0.010 active=True motion_flag=False avg_power=0.005664
008 presence=0.556 motion=0.010 active=True motion_flag=False avg_power=0.005664
009 presence=0.568 motion=0.015 active=True motion_flag=False avg_power=0.005664
010 presence=0.576 motion=0.018 active=True motion_flag=False avg_power=0.005664
011 presence=0.583 motion=0.017 active=True motion_flag=False avg_power=0.005664
012 presence=0.588 motion=0.036 active=True motion_flag=False avg_power=0.005664
013 presence=0.592 motion=0.031 active=True motion_flag=False avg_power=0.005664
014 presence=0.594 motion=0.025 active=True motion_flag=False avg_power=0.005664
015 presence=0.597 motion=0.031 active=True motion_flag=False avg_power=0.005664
016 presence=0.598 motion=0.037 active=True motion_flag=False avg_power=0.005664
017 presence=0.600 motion=0.041 active=True motion_flag=False avg_power=0.005664
018 presence=0.603 motion=0.125 active=True motion_flag=False avg_power=0.005664
019 presence=0.609 motion=0.273 active=True motion_flag=False avg_power=0.005664
020 presence=0.622 motion=0.625 active=True motion_flag=False avg_power=0.005664
021 presence=0.634 motion=0.676 active=True motion_flag=False avg_power=0.005664
022 presence=0.638 motion=0.497 active=True motion_flag=False avg_power=0.005664
023 presence=0.639 motion=0.442 active=True motion_flag=False avg_power=0.005664
024 presence=0.637 motion=0.285 active=True motion_flag=False avg_power=0.005664
025 presence=0.635 motion=0.287 active=True motion_flag=False avg_power=0.005664
026 presence=0.635 motion=0.364 active=True motion_flag=False avg_power=0.005664
027 presence=0.638 motion=0.476 active=True motion_flag=False avg_power=0.005664
028 presence=0.645 motion=0.654 active=True motion_flag=False avg_power=0.005664
029 presence=0.653 motion=0.753 active=True motion_flag=False avg_power=0.005664
030 presence=0.655 motion=0.608 active=True motion_flag=False avg_power=0.005664
031 presence=0.648 motion=0.298 active=True motion_flag=False avg_power=0.005664
032 presence=0.639 motion=0.111 active=True motion_flag=False avg_power=0.005664
033 presence=0.632 motion=0.095 active=True motion_flag=False avg_power=0.005664
034 presence=0.626 motion=0.082 active=True motion_flag=False avg_power=0.005664
035 presence=0.621 motion=0.081 active=True motion_flag=False avg_power=0.005664
036 presence=0.619 motion=0.122 active=True motion_flag=False avg_power=0.005664
037 presence=0.618 motion=0.134 active=True motion_flag=False avg_power=0.005664
038 presence=0.617 motion=0.159 active=True motion_flag=False avg_power=0.005664
039 presence=0.619 motion=0.258 active=True motion_flag=False avg_power=0.005664
040 presence=0.626 motion=0.457 active=True motion_flag=False avg_power=0.005664
041 presence=0.638 motion=0.726 active=True motion_flag=False avg_power=0.005664
042 presence=0.647 motion=0.743 active=True motion_flag=False avg_power=0.005664
043 presence=0.648 motion=0.524 active=True motion_flag=False avg_power=0.005664
044 presence=0.647 motion=0.427 active=True motion_flag=False avg_power=0.005664
045 presence=0.641 motion=0.221 active=True motion_flag=False avg_power=0.005664
046 presence=0.635 motion=0.165 active=True motion_flag=False avg_power=0.005664
047 presence=0.629 motion=0.139 active=True motion_flag=False avg_power=0.005664
048 presence=0.625 motion=0.113 active=True motion_flag=False avg_power=0.005664
049 presence=0.622 motion=0.126 active=True motion_flag=False avg_power=0.005664
050 presence=0.623 motion=0.256 active=True motion_flag=False avg_power=0.005664
051 presence=0.627 motion=0.386 active=True motion_flag=False avg_power=0.005664
052 presence=0.634 motion=0.559 active=True motion_flag=False avg_power=0.005664
053 presence=0.641 motion=0.617 active=True motion_flag=False avg_power=0.005664
054 presence=0.645 motion=0.577 active=True motion_flag=False avg_power=0.005664
055 presence=0.645 motion=0.430 active=True motion_flag=False avg_power=0.005664
056 presence=0.640 motion=0.254 active=True motion_flag=False avg_power=0.005664
057 presence=0.635 motion=0.199 active=True motion_flag=False avg_power=0.005664
058 presence=0.631 motion=0.186 active=True motion_flag=False avg_power=0.005664
059 presence=0.628 motion=0.177 active=True motion_flag=False avg_power=0.005664
060 presence=0.626 motion=0.214 active=True motion_flag=False avg_power=0.005664
061 presence=0.627 motion=0.296 active=True motion_flag=False avg_power=0.005664
062 presence=0.631 motion=0.442 active=True motion_flag=False avg_power=0.005664
063 presence=0.635 motion=0.452 active=True motion_flag=False avg_power=0.005664
064 presence=0.643 motion=0.677 active=True motion_flag=False avg_power=0.005664
065 presence=0.649 motion=0.675 active=True motion_flag=False avg_power=0.005664
066 presence=0.647 motion=0.411 active=True motion_flag=False avg_power=0.005664
067 presence=0.641 motion=0.221 active=True motion_flag=False avg_power=0.005664
068 presence=0.637 motion=0.237 active=True motion_flag=False avg_power=0.005664
069 presence=0.633 motion=0.226 active=True motion_flag=False avg_power=0.005664
070 presence=0.629 motion=0.179 active=True motion_flag=False avg_power=0.005664
071 presence=0.631 motion=0.346 active=True motion_flag=False avg_power=0.005664
072 presence=0.636 motion=0.536 active=True motion_flag=False avg_power=0.005664
073 presence=0.644 motion=0.663 active=True motion_flag=False avg_power=0.005664
074 presence=0.650 motion=0.693 active=True motion_flag=False avg_power=0.005664
075 presence=0.648 motion=0.400 active=True motion_flag=False avg_power=0.005664
076 presence=0.642 motion=0.255 active=True motion_flag=False avg_power=0.005664
077 presence=0.635 motion=0.149 active=True motion_flag=False avg_power=0.005664
078 presence=0.630 motion=0.137 active=True motion_flag=False avg_power=0.005664
079 presence=0.626 motion=0.125 active=True motion_flag=False avg_power=0.005664



