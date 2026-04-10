# Four Scenario Quick Run (Jetson)

## 1) Verify Camera Mapping

```bash
v4l2-ctl --list-devices
ls -l /dev/v4l/by-id/
```

Expected mapping in this setup:
- RGB webcam (Logitech C920): `/dev/video0` or `/dev/video1`
- Thermal (PureThermal): `/dev/video2` or `/dev/video3`

## 2) Run One Combined MP4 (All 4 Scenarios)

This creates one single video with:
- RGB camera
- Thermal camera
- mmWave point cloud
- Presence panel

```bash
cd ~/Desktop/SCANU-dev_adrian
PYTHONPATH=. python3 software/layer1_sensor_hub/testing/four_scenario_multisensor_capture.py \
  --rgb-device /dev/video0 \
  --thermal-device 2 \
  --rgb-fourcc auto \
  --presence off \
  --capture-mode video \
  --combined-video /home/insu/Desktop/collecting_data/four_scenario_multisensor/run_all_scenarios.mp4 \
  --combined-video-only \
  --capture-seconds 20
```

If thermal does not look right, change only:
- `--thermal-device 2` -> `--thermal-device 3`

If RGB does not look right, change only:
- `--rgb-device /dev/video0` -> `--rgb-device /dev/video1`

## 3) Optional Point Cloud Tuning (More Density)

Add these flags:

```bash
--mmwave-trail-frames 24 \
--mmwave-voxel-size-m 0.06 \
--mmwave-min-voxel-hits 1 \
--mmwave-min-snr-db 1.2
```























---------------------------------------

insu@insu-desktop:~$ cd ~/Desktop/SCANU-dev_adrian
PYTHONPATH=. python3 software/layer1_sensor_hub/testing/four_scenario_multisensor_capture.py \
  --rgb-device /dev/video0 \
  --thermal-device 2 \
  --rgb-fourcc auto \
  --presence off \
  --capture-mode video \
  --combined-video /home/insu/Desktop/collecting_data/four_scenario_multisensor/run_all_scenarios.mp4 \
  --combined-video-only \
  --capture-seconds 20
[INIT] Opening sensors...
[INIT] mmWave ports CLI=/dev/ttyUSB0 DATA=/dev/ttyUSB1
[INIT] Output dir: /home/insu/Desktop/collecting_data/four_scenario_multisensor
[INIT] RGB camera: /dev/video0
[INIT] Thermal camera: /dev/video2
[INIT] Combined video output: /home/insu/Desktop/collecting_data/four_scenario_multisensor/run_all_scenarios.mp4

========================================================================
Scenario 1/4: empty_room -> Room only (no person)
Press Enter to start (s=skip, q=quit): 
[CAPTURE] empty_room: recording 20.0s ...
TLV 113051376 truncated (need 116459233, have 64)
TLV 111609558 truncated (need 116000401, have 64)
TLV 108398281 truncated (need 105907810, have 64)
[SAVED] appended to combined video: /home/insu/Desktop/collecting_data/four_scenario_multisensor/run_all_scenarios.mp4
[SAVED] /home/insu/Desktop/collecting_data/four_scenario_multisensor/session_0001_empty_room_20260410T162239_capture.json

========================================================================
Scenario 2/4: person_unarmed -> Person unarmed
Press Enter to start (s=skip, q=quit): 
[CAPTURE] person_unarmed: recording 20.0s ...
TLV 119474121 truncated (need 131598226, have 68)
TLV 50659332 truncated (need 1152, have 1104)
TLV 105776742 truncated (need 113313464, have 64)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 112133722 truncated (need 105055815, have 64)
TLV 50659332 truncated (need 1152, have 1104)
[SAVED] appended to combined video: /home/insu/Desktop/collecting_data/four_scenario_multisensor/run_all_scenarios.mp4
[SAVED] /home/insu/Desktop/collecting_data/four_scenario_multisensor/session_0002_person_unarmed_20260410T162301_capture.json

========================================================================
Scenario 3/4: person_armed_concealed -> Person with concealed weapon
Press Enter to start (s=skip, q=quit): 
[CAPTURE] person_armed_concealed: recording 20.0s ...
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 114624228 truncated (need 115476226, have 68)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 50659332 truncated (need 1152, have 1104)
TLV 108463908 truncated (need 109250166, have 64)
TLV 167774225 truncated (need 185666274, have 64)
TLV 114689623 truncated (need 116131570, have 64)
[SAVED] appended to combined video: /home/insu/Desktop/collecting_data/four_scenario_multisensor/run_all_scenarios.mp4
[SAVED] /home/insu/Desktop/collecting_data/four_scenario_multisensor/session_0003_person_armed_concealed_20260410T162338_capture.json

========================================================================
Scenario 4/4: person_armed_visible -> Pers

