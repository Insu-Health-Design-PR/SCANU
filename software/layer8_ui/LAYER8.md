# Layer 8 Jetson Runbook

This checkout serves the Layer 8 dashboard from `software/layer8_ui/static`.
There is no in-repo `software/layer8_ui/frontend` npm app.

## Setup

```bash
cd ~/Desktop/SCANU/software/layer8_ui
INSTALL_SYSTEM_DEPS=1 ./scripts/layer8.sh setup
```

The Python environment is created at:

```text
~/Desktop/SCANU/software/.venv
```

## Start

```bash
cd ~/Desktop/SCANU/software/layer8_ui
./scripts/layer8.sh start
```

Open:

```text
http://<JETSON_IP>:8088
```

Optional API key:

```bash
LAYER8_API_KEY="change-this-key" ./scripts/layer8.sh start
```

## Check

```bash
./scripts/layer8.sh check
```

With API key:

```bash
LAYER8_API_KEY="change-this-key" ./scripts/layer8.sh check
```

## Sensors

```bash
./scripts/layer8.sh run-all
./scripts/layer8.sh stop-all
```

## Useful Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_HOST` | `0.0.0.0` | Bind host for uvicorn. |
| `BACKEND_PORT` | `8088` | Backend/UI port. |
| `INSTALL_SYSTEM_DEPS` | `0` | Install apt packages during setup. |
| `INSTALL_LAYER4_FULL` | `0` | Install full Layer 4 requirements. |
| `LAYER8_API_KEY` | empty | Protect `/api/*` and WebSockets. |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ensurepip` / venv failure | `sudo apt install -y python3-venv python3-pip`, then rerun setup. |
| `ModuleNotFoundError: layer8_ui` | Run commands from `software/layer8_ui` through `./scripts/layer8.sh`. |
| Port `8088` busy | `BACKEND_PORT=8089 ./scripts/layer8.sh start`. |
| Radar missing | Check `ls /dev/ttyUSB*` and `software/layer8_ui/ui_settings.json`. |
| Camera missing | Check `v4l2-ctl --list-devices`. |
