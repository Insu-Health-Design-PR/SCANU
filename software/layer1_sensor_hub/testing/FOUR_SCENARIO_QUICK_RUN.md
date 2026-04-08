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
