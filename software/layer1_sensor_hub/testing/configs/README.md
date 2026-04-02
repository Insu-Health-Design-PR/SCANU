# mmWave Config Files for Testing V2

Place your mmWave `.cfg` files in this folder.

Recommended default filename:

- `mmwave_main.cfg`

Scripts in `software/layer1_sensor_hub/testing` that run mmWave now expect a config file path and use file-based configuration instead of static in-code defaults.

Examples:

- `run_live_hub.py --config software/layer1_sensor_hub/testing/configs/mmwave_main.cfg`
- `capture_mmwave_json.py --config software/layer1_sensor_hub/testing/configs/mmwave_main.cfg`

Notes:

- If the file does not exist, those scripts will fail with a clear error message.
- Keep one stable profile here for repeatable testing.


## Risk Config For Concealed Game Prop (Rich Capture)

For `capture_all_sensors_rich.py`, you can use:

- Named profile: `--risk-profile concealed_game_prop`
- JSON file: `--risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json`

Example:

```bash
python3 software/layer1_sensor_hub/testing/capture_all_sensors_rich.py \
  --config software/layer1_sensor_hub/testing/configs/stable_tracking_indoor4.cfg \
  --risk-config software/layer1_sensor_hub/testing/configs/risk_concealed_game_prop.json \
  --frames 300 \
  --interval-s 0.1 \
  --video software/layer1_sensor_hub/testing/view/all_sensors_rich_concealed.mp4 \
  --output software/layer1_sensor_hub/testing/view/all_sensors_rich_concealed.json
```

Important: this is a heuristic profile for experiments. It is not a certified safety/security detector.

- `stable_tracking_weapon_detection.cfg`: experimental indoor profile for concealed-object screening tests.
