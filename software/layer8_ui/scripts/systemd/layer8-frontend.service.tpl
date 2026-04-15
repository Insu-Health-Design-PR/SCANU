[Unit]
Description=SCAN-U Layer8 Frontend (Vite)
After=network-online.target layer8-backend.service
Wants=network-online.target

[Service]
Type=simple
User=__USER__
WorkingDirectory=__ROOT__/software/layer8_ui/frontend
Environment=NODE_ENV=development
EnvironmentFile=-/etc/default/layer8
ExecStart=/bin/bash -lc '
  cd "__ROOT__/software/layer8_ui/frontend"; \
  VITE_LAYER8_API_BASE="http://127.0.0.1:${LAYER8_BACKEND_PORT:-8080}" \
  VITE_LAYER8_WS_URL="ws://127.0.0.1:${LAYER8_BACKEND_PORT:-8080}/ws/events" \
  node node_modules/vite/bin/vite.js \
    --host "${LAYER8_HOST:-0.0.0.0}" \
    --port "${LAYER8_FRONTEND_PORT:-4173}" \
    --strictPort
'
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
