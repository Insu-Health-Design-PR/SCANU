# Layer 8 Jetson Demo Scripts (Setup + Run)

This guide prepares a Jetson device to run Layer 8 backend + sensors, open a Cloudflare tunnel, and connect from a Vercel frontend.

## Files Added

- `software/layer8_ui/scripts/setup_layer8_jetson_demo.sh`
- `software/layer8_ui/scripts/run_layer8_jetson_vercel_demo.sh`

## 1) Setup (create venv, install/update dependencies)

From the repository root on Jetson:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
chmod +x scripts/setup_layer8_jetson_demo.sh scripts/run_layer8_jetson_vercel_demo.sh
./scripts/setup_layer8_jetson_demo.sh
```

If setup fails with an `ensurepip` / `virtual environment was not created successfully` error, run:

```bash
cd ~/Desktop/SCANU-dev_adrian/software
sudo apt update
sudo apt install -y python3-venv python3-pip
sudo apt install -y python3.8-venv || true
sudo apt install -y python3.10-venv || true
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

Then return to Layer 8 and run setup again:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/setup_layer8_jetson_demo.sh
```

Optional flags:

```bash
# Also install apt packages
INSTALL_SYSTEM_DEPS=1 ./scripts/setup_layer8_jetson_demo.sh

# Skip npm install
INSTALL_NODE_DEPS=0 ./scripts/setup_layer8_jetson_demo.sh

# Install full Layer 4 requirements (may replace Jetson torch wheels)
INSTALL_LAYER4_FULL=1 ./scripts/setup_layer8_jetson_demo.sh
```

## 2) Run Demo (backend + local checks + sensors + tunnel)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
LAYER8_API_KEY="change-this-key" ./scripts/run_layer8_jetson_vercel_demo.sh
```

What this script does:

1. Activates `software/.venv`
2. Starts backend with Vercel-safe settings (`0.0.0.0:8088`, CORS origin)
3. Waits for `/api/health`
4. Runs authenticated endpoint checks
5. Starts sensors with `/api/run_all` (default enabled)
6. Opens Cloudflare tunnel

## 3) Configure Vercel Frontend

When the tunnel URL appears (example: `https://abc.trycloudflare.com`), configure:

```text
VITE_LAYER8_API_BASE=https://abc.trycloudflare.com
VITE_LAYER8_WS_URL=wss://abc.trycloudflare.com/ws/events
VITE_LAYER8_API_KEY=change-this-key
```

Redeploy the frontend.

## 4) Public Validation

In another terminal:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
BACKEND_URL="https://abc.trycloudflare.com" \
LAYER8_API_KEY="change-this-key" \
./scripts/check_layer8_backend.sh
```

## 5) Useful Runtime Options

```bash
# Do not auto-start sensors
AUTO_START_SENSORS=0 LAYER8_API_KEY="change-this-key" ./scripts/run_layer8_jetson_vercel_demo.sh

# Custom backend port
BACKEND_PORT=8089 LAYER8_API_KEY="change-this-key" ./scripts/run_layer8_jetson_vercel_demo.sh
```

## 6) Troubleshooting

- `cloudflared not found`: install Cloudflare Tunnel and ensure it is in `PATH`.
- `npm not found`: install Node.js 20.
- `401` on protected endpoints: verify `LAYER8_API_KEY` matches Jetson backend key.
- no camera/radar data: verify `v4l2-ctl --list-devices`, `/dev/ttyUSB*`, and `software/layer8_ui/ui_settings.json`.
- backend start failure: inspect `software/layer8_ui/logs/backend.vercel.demo.log`.
- `ensurepip` / `venv` failure: install `python3-venv` (and version-specific `python3.8-venv`/`python3.10-venv` when needed), remove `.venv`, and recreate it.
