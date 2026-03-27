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

