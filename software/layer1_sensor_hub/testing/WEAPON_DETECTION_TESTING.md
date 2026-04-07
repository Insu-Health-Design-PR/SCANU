# Weapon Detection Screening (Experimental)

This guide uses camera + mmWave + Infineon to run an **experimental screening** workflow for concealed object patterns.

Important:
- This is a heuristic screening flow.
- It is **not** a certified weapon detector.
- Always treat `ALERT` as a prompt for manual review, not final proof.

## 1) Recommended Config Files

- mmWave profile:
  - `software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_v2.cfg`
  - `software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg` (fallback)
- Risk profile:
  - `software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json`

## 2) Preflight (Connectivity)

```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py
```

If you need explicit ports:

```bash
python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py \
  --cli-port /dev/ttyUSB0 \
  --data-port /dev/ttyUSB1 \
  --thermal-device 0
```

## 3) Rich Capture With New Weapon Config

```bash
python3 software/layer1_sensor_hub/testing/capture_all_sensors_rich.py \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 300 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/weapon_screening_rich.mp4 \
  --output software/layer1_sensor_hub/testing/view/weapon_screening_rich.json
```

## 4) Full Screening Test (Capture + Report)

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 300 \
  --interval-s 0.1 \
  --mmwave-risk-th 0.45 \
  --presence-th 0.55 \
  --thermal-delta-th 6.0 \
  --min-consecutive 6 \
  --video software/layer1_sensor_hub/testing/view/weapon_screening.mp4 \
  --capture-json software/layer1_sensor_hub/testing/view/weapon_screening_capture.json \
  --report-json software/layer1_sensor_hub/testing/view/weapon_screening_report.json
```

## 5) Interpreting Output

`NO_ALERT`:
- No suspicious segment matched your thresholds and persistence criteria.

`ALERT`:
- One or more suspicious segments were found.
- Check:
  - `max_mmwave_risk`
  - `max_presence`
  - `max_thermal_delta`
- Review the MP4 and capture JSON before any operational decision.

## 6) Tuning Tips

If detections are too weak (misses):
- Lower `--mmwave-risk-th` (example: `0.40`)
- Lower `--presence-th` (example: `0.50`)
- Lower `--min-consecutive` (example: `4`)

If false positives are high:
- Raise `--mmwave-risk-th` (example: `0.55`)
- Raise `--presence-th` (example: `0.65`)
- Raise `--min-consecutive` (example: `8`)

## 7) No-IFX Preset (mmWave + Thermal)

Use this when the presence sensor is unavailable or unstable.

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 450 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/weapon_screening_no_ifx.mp4 \
  --capture-json software/layer1_sensor_hub/testing/view/weapon_screening_no_ifx_capture.json \
  --report-json software/layer1_sensor_hub/testing/view/weapon_screening_no_ifx_report.json
```

`--mode no_ifx` applies these tuned values automatically:
- `--presence off`
- `--mmwave-risk-th 0.07`
- `--presence-th 1.0` (effectively disabled)
- `--thermal-delta-th 4.0`
- `--min-consecutive 4`

## 8) Verify Local Branch/Script Before Running `--mode`

Run this first to ensure your local copy includes the latest `--mode no_ifx` support:

```bash
cd /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU
git checkout dev_adrian
git pull --ff-only origin dev_adrian
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py --help | grep mode
```

## 9) Commands Used In Jetson (No IFX)

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py --help | grep mode

python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py --skip-infineon

python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json

cat software/layer1_sensor_hub/testing/view/weapon_screening_no_ifx_report.json
```

## 10) Run With Sensitivity Config (No IFX)

```bash
python3 /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --config /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg \
  --risk-config /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 450 \
  --interval-s 0.1 \
  --video /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer1_sensor_hub/testing/view/weapon_screening_sens.mp4 \
  --capture-json /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer1_sensor_hub/testing/view/weapon_screening_sens_capture.json \
  --report-json /Users/adriancordero/Desktop/SCANU-dev_adrian/SCANU/software/layer1_sensor_hub/testing/view/weapon_screening_sens_report.json
```

## 11) Three-Scenario Comparison Test

Run one full cycle with these scenarios in order:
1. `empty_room`
2. `person_unarmed`
3. `person_concealed_object`

The script pauses before each scenario (press Enter to continue), and generates a combined comparison report.

```bash
python3 software/layer1_sensor_hub/testing/three_scenario_comparison_test.py \
  --mode no_ifx \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 350 \
  --interval-s 0.1 \
  --output-prefix school_airport_trial
```

Output report example:
- `software/layer1_sensor_hub/testing/view/school_airport_trial_comparison_report.json`

## 12) Temporal Fusion (Recommended)

The screening logic now supports temporal fusion, where mmWave is primary and thermal can support within a nearby frame window.

Single run example:

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --fusion-mode mm_primary_temporal \
  --thermal-support-window 12 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 450 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/weapon_screening_temporal.mp4 \
  --capture-json software/layer1_sensor_hub/testing/view/weapon_screening_temporal_capture.json \
  --report-json software/layer1_sensor_hub/testing/view/weapon_screening_temporal_report.json
```

Three-scenario comparison with temporal fusion:

```bash
python3 software/layer1_sensor_hub/testing/three_scenario_comparison_test.py \
  --mode no_ifx \
  --fusion-mode mm_primary_temporal \
  --thermal-support-window 12 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 350 \
  --interval-s 0.1 \
  --output-prefix school_airport_trial_temporal
```

## 13) V2 Tuning For Concealed Object Detection

Use this sequence in order:

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py --help | grep -E "mode|fusion-mode|thermal-support-window"

python3 software/layer1_sensor_hub/testing/sensor_approval_hub.py --skip-infineon

python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --fusion-mode mm_primary_score_boost \
  --thermal-support-window 12 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_v2.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --mmwave-risk-th 0.06 \
  --thermal-delta-th 3.5 \
  --min-consecutive 3 \
  --frames 450 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/weapon_screening_v2.mp4 \
  --capture-json software/layer1_sensor_hub/testing/view/weapon_screening_v2_capture.json \
  --report-json software/layer1_sensor_hub/testing/view/weapon_screening_v2_report.json

python3 software/layer1_sensor_hub/testing/three_scenario_comparison_test.py \
  --mode no_ifx \
  --fusion-mode mm_primary_score_boost \
  --thermal-support-window 12 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_v2.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 350 \
  --interval-s 0.1 \
  --output-prefix school_airport_trial_v2

cat software/layer1_sensor_hub/testing/view/school_airport_trial_v2_comparison_report.json
```

## 14) Distance Campaign (5ft / 10ft / 20ft)

This campaign runs an operator-guided sequence and saves **video + capture JSON + report JSON** for each case.
You will press Enter before each run.

```bash
python3 software/layer1_sensor_hub/testing/weapon_distance_campaign.py \
  --mode no_ifx \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_v2.cfg \[CAPTURING]
/usr/bin/python3 /home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/capture_all_sensors_rich.py --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json --frames 200 --interval-s 0.1 --mmwave-timeout-ms 200 --presence off --thermal-device 0 --thermal-width 640 --thermal-height 480 --thermal-fps 30 --video /home/insu/Desktop/collecting_data/unsafe/concealed_weapon/unsafe_concealed_weapon_5ft_r01_20260406T153402.mp4 --output /home/insu/Desktop/collecting_data/unsafe/concealed_weapon/unsafe_concealed_weapon_5ft_r01_20260406T153402_capture.json
                                                                                                                                                                       
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --plan software/layer1_sensor_hub/testing/configs/weapon_distance_campaign_plan.json \
  --fusion-mode mm_primary_score_boost \
  --thermal-support-window 12 \
  --mmwave-risk-th 0.06 \
  --thermal-delta-th 3.5 \
  --min-consecutive 3 \
  --frames 350 \
  --interval-s 0.1 \
  --campaign-name school_airport_distance_v1
```

Output folder:

- `software/layer1_sensor_hub/testing/view/weapon_distance_campaign/school_airport_distance_v1/`

Campaign outputs:

- One `.mp4` per case
- One `_capture.json` per case
- One `_report.json` per case
- `campaign_results.json`
- `campaign_results.csv`
- `campaign_summary.md`

Fusion mode note:
- `mm_primary_score_boost` keeps mmWave as primary signal and uses thermal/presence as confidence boost (recommended for concealed-object runs where thermal can be intermittent).

## 15) Quick Run V2 (Recommended)

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --fusion-mode mm_primary_score_boost \
  --thermal-support-window 12 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_v2.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --mmwave-risk-th 0.06 \
  --thermal-delta-th 3.5 \
  --min-consecutive 3 \
  --frames 450 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/weapon_screening_v2_boost.mp4 \
  --capture-json software/layer1_sensor_hub/testing/view/weapon_screening_v2_boost_capture.json \
  --report-json software/layer1_sensor_hub/testing/view/weapon_screening_v2_boost_report.json
```

## 16) Two People Test (One Threat, One No Threat) - Sensitivity Config

Recommended setup:
- Two subjects in frame.
- Subject A: no threat item.
- Subject B: concealed replica (waist/back or bag).
- Keep both visible while walking/pausing for at least 30-45 seconds.

```bash
python3 software/layer1_sensor_hub/testing/concealed_weapon_screening_test.py \
  --mode no_ifx \
  --fusion-mode mm_primary_score_boost \
  --thermal-support-window 12 \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --mmwave-risk-th 0.06 \
  --thermal-delta-th 3.5 \
  --min-consecutive 3 \
  --frames 450 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/two_people_one_threat_sens.mp4 \
  --capture-json software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_capture.json \
  --report-json software/layer1_sensor_hub/testing/view/two_people_one_threat_sens_report.json
```

## 17) Interactive Dataset Collection Menu (Safe/Unsafe)

This menu-driven runner is designed for collecting training data with minimal manual work.
It stores data in:

- `/home/insu/Desktop/collecting_data/safe/...`
- `/home/insu/Desktop/collecting_data/unsafe/...`

For each run it saves:

- `.mp4` video
- `_capture.json`
- `_report.json`
- `manifest.jsonl` (dataset index)

Menu behavior:

- Choose `SAFE` or `UNSAFE`
- Choose scenario
- Enter distance
- Press Enter to run
- After each run:
  - `Enter` = next run (same scenario/distance, auto-increment run id)
  - `r` = repeat last test
  - `m` = return to main menu
  - `exit` = stop

Current `UNSAFE` scenarios in the menu:

- `armed_on_body`
- `concealed_object`
- `concealed_weapon`
- `threat_in_bag`
- `two_people_one_weapon`

```bash
python3 software/layer1_sensor_hub/testing/interactive_dataset_collector.py \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_weapon_detection_sensitivity.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --out-base /home/insu/Desktop/collecting_data \
  --frames 350 \
  --interval-s 0.1 \
  --presence ifx
```

## 18) Thermal Weapon Views (Single Folder + Menu + Auto Name)

This runner captures thermal still images in one folder and labels each image by selected view:

- `front_view`
- `back_view`
- `side_view`

Behavior:

- Uses menu to pick view for each capture block.
- Stores all images in a single output folder.
- Auto-names files with view + session + incremental index.
- Writes a manifest JSON for the full session.

```bash
python3 software/layer1_sensor_hub/testing/capture_thermal_weapon_views.py \
  --out-dir /home/insu/Desktop/collecting_data/thermal_weapon_views \
  --images-per-view 30 \
  --thermal-device 0 \
  --manual
```

Example output filename:

- `thermal_front_view_20260407T120501_0001.png`

## 19) Dual Camera Menu (Logitech USB + Thermal)

Capture from both cameras at the same time with menu options:

- `1` photo (saves RGB + thermal images)
- `2` video (saves RGB + thermal videos)
- `3` exit

Auto-detection:

- `--rgb-device auto` tries to select Logitech/C920 first.
- If auto fails, set RGB explicitly using index (`--rgb-device 2`) or path (`--rgb-device /dev/video2`).
- You can list V4L2 devices with `--list-cameras`.

```bash
python3 software/layer1_sensor_hub/testing/capture_dual_camera_menu.py --list-cameras
```

```bash
python3 software/layer1_sensor_hub/testing/capture_dual_camera_menu.py \
  --out-dir /home/insu/Desktop/collecting_data/dual_camera \
  --rgb-device auto \
  --thermal-device 0 \
  --default-video-seconds 10
```

Explicit Jetson example (Logitech on `/dev/video2`):

```bash
python3 software/layer1_sensor_hub/testing/capture_dual_camera_menu.py \
  --out-dir /home/insu/Desktop/collecting_data/dual_camera \
  --rgb-device /dev/video2 \
  --thermal-device 0 \
  --default-video-seconds 20
```

Notes:

- Console states now show clear progress: `PREPARING`, `RECORDING`, `SAVING`, `DONE`.
- The script estimates effective camera FPS and writes videos with adjusted FPS to reduce short/fast playback artifacts.
- Increase duration with `--default-video-seconds 20` (or higher) if needed.
