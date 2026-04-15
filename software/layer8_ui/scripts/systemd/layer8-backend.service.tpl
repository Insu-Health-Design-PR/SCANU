[Unit]
Description=SCAN-U Layer8 Backend (Live Stack)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=__USER__
WorkingDirectory=__ROOT__
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=__ROOT__
EnvironmentFile=-/etc/default/layer8
ExecStart=/bin/bash -lc '
  source "${LAYER8_VENV:-__ROOT__/.venv/bin/activate}"; \
  cd "__ROOT__/software/layer8_ui"; \
  IFX_ARG=""; \
  if [[ -n "${LAYER8_IFX_UUID:-}" ]]; then IFX_ARG="--ifx-uuid ${LAYER8_IFX_UUID}"; fi; \
  PYTHONPATH="__ROOT__" python3 -m software.layer8_ui.backend.run_layer8_stack \
    --mode live \
    --host "${LAYER8_HOST:-0.0.0.0}" \
    --port "${LAYER8_BACKEND_PORT:-8080}" \
    --radar-id "${LAYER8_RADAR_ID:-radar_main}" \
    --cli-port "${LAYER8_CLI_PORT:-/dev/ttyUSB0}" \
    --data-port "${LAYER8_DATA_PORT:-/dev/ttyUSB1}" \
    --config "${LAYER8_CONFIG_PATH:-software/layer1_sensor_hub/testing/configs/full_config.cfg}" \
    --mmwave "${LAYER8_MMWAVE:-on}" \
    --presence "${LAYER8_PRESENCE:-ifx}" \
    --thermal "${LAYER8_THERMAL:-on}" \
    --thermal-device "${LAYER8_THERMAL_DEVICE:-0}" \
    --thermal-width "${LAYER8_THERMAL_WIDTH:-640}" \
    --thermal-height "${LAYER8_THERMAL_HEIGHT:-480}" \
    --thermal-fps "${LAYER8_THERMAL_FPS:-30}" \
    --rgb "${LAYER8_RGB:-on}" \
    --rgb-device "${LAYER8_RGB_DEVICE:-0}" \
    --rgb-width "${LAYER8_RGB_WIDTH:-640}" \
    --rgb-height "${LAYER8_RGB_HEIGHT:-480}" \
    --rgb-fps "${LAYER8_RGB_FPS:-30}" \
    --visual "${LAYER8_VISUAL:-on}" \
    --visual-width "${LAYER8_VISUAL_WIDTH:-640}" \
    --visual-height "${LAYER8_VISUAL_HEIGHT:-480}" \
    --mmwave-timeout-ms "${LAYER8_MMWAVE_TIMEOUT_MS:-200}" \
    --interval-s "${LAYER8_INTERVAL_S:-0.2}" \
    --max-frames 0 \
    ${IFX_ARG}
'
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
