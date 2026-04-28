# Run `dev_kpr-layer8` On Jetson

This document is stored in the `dev_adrian` branch on purpose, but it describes how to run the separate demo branch:

```text
dev_kpr-layer8
```

Use this when the Jetson has both branches/repo states available and you want to run the KPR Layer 8 demo, not the newer `dev_adrian` Vercel/Cloudflare setup.

## Important Difference

`dev_kpr-layer8` is a local Jetson demo branch.

It serves the UI directly from the Layer 8 backend:

```text
http://<JETSON_IP>:8088/
```

It does not use:

```text
https://scanu-ui.vercel.app
Cloudflare Tunnel
LAYER8_API_KEY
VITE_LAYER8_API_BASE
VITE_LAYER8_WS_URL
```

The Vercel frontend belongs to the newer `dev_adrian` flow. For `dev_kpr-layer8`, open the backend-served dashboard directly.

## Jetson Paths

Expected repo path on Jetson:

```bash
~/Desktop/SCANU-dev_adrian
```

Layer 8 path:

```bash
~/Desktop/SCANU-dev_adrian/software/layer8_ui
```

## 1) Get The Correct Branch

If the repo already exists on the Jetson:

```bash
cd ~/Desktop/SCANU-dev_adrian
git fetch origin
git checkout dev_kpr-layer8
git pull origin dev_kpr-layer8
```

If the repo does not exist yet:

```bash
cd ~/Desktop
git clone https://github.com/Insu-Health-Design-PR/SCANU.git SCANU-dev_adrian
cd ~/Desktop/SCANU-dev_adrian
git checkout dev_kpr-layer8
```

Confirm branch:

```bash
git branch --show-current
```

Expected:

```text
dev_kpr-layer8
```

## 2) Install System Dependencies

```bash
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-venv \
  git \
  curl \
  v4l-utils \
  ffmpeg \
  libgl1 \
  libglib2.0-0
```

Check cameras:

```bash
v4l2-ctl --list-devices
```

Check radar/mmWave serial ports:

```bash
ls /dev/ttyUSB*
```

## 3) Create Python Environment

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
```

## 4) Install Python Dependencies

Minimum Layer 8 backend:

```bash
pip install -r layer8_ui/requirements.txt
```

Radar/mmWave support:

```bash
pip install -r layer1_radar/requirements.txt
```

Weapon AI / Layer 4 support:

```bash
pip install -r layer4_inference/requirements.txt
```

### Jetson PyTorch Note

On Jetson, do not blindly reinstall `torch` and `torchvision` if they are already installed through NVIDIA/JetPack.

Check first:

```bash
python3 - <<'PY'
import torch
print('torch:', torch.__version__)
try:
    import torchvision
    print('torchvision:', torchvision.__version__)
except Exception as exc:
    print('torchvision import failed:', exc)
PY
```

If `torch` or `torchvision` fails, install versions compatible with your JetPack/NVIDIA image instead of generic desktop wheels.

## 5) Run Layer 8 Demo Backend

From the `software` directory:

```bash
cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

The backend serves the dashboard at:

```text
http://127.0.0.1:8088/
```

From another machine on Tailscale, use the Jetson Tailscale IP:

```text
http://100.92.1.128:8088/
```

## 6) Test Backend Endpoints

From the Jetson:

```bash
curl http://127.0.0.1:8088/api/status
```

From your Mac through Tailscale:

```bash
curl http://100.92.1.128:8088/api/status
```

## 7) Start / Stop Sensors From Terminal

Start all sensors:

```bash
curl -X POST http://127.0.0.1:8088/api/run_all
```

Check status:

```bash
curl http://127.0.0.1:8088/api/status
```

Stop all sensors:

```bash
curl -X POST http://127.0.0.1:8088/api/stop_all
```

Restart all sensors:

```bash
curl -X POST http://127.0.0.1:8088/api/restart_all
```

You can also use the UI buttons in:

```text
http://100.92.1.128:8088/
```

## 8) Open Direct Views

Full dashboard:

```text
http://100.92.1.128:8088/
```

Thermal only:

```text
http://100.92.1.128:8088/embed/thermal
```

Webcam only:

```text
http://100.92.1.128:8088/embed/webcam
```

## 9) Current Device Defaults In `dev_kpr-layer8`

The branch settings use these defaults in `software/layer8_ui/ui_settings.json`:

```text
thermal_device: 1
webcam_device: 2
mmwave cli_port: /dev/ttyUSB0
mmwave data_port: /dev/ttyUSB1
backend port: 8088
```

If a camera index is wrong, check devices:

```bash
v4l2-ctl --list-devices
```

Then update settings from the UI or edit:

```text
software/layer8_ui/ui_settings.json
```

## 10) One-Shot Command Sequence

Use this after dependencies are installed:

```bash
cd ~/Desktop/SCANU-dev_adrian
git fetch origin
git checkout dev_kpr-layer8
git pull origin dev_kpr-layer8
cd software
source .venv/bin/activate
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Then open:

```text
http://100.92.1.128:8088/
```

## Troubleshooting

### Port 8088 Already In Use

```bash
lsof -i :8088
```

Stop the process shown, or run on another port:

```bash
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8089
```

Then open:

```text
http://100.92.1.128:8089/
```

### Cannot Access From Mac

Confirm Jetson Tailscale IP:

```bash
tailscale ip -4
```

Confirm backend is listening on all interfaces:

```bash
ss -ltnp | grep 8088
```

Expected host should be `0.0.0.0:8088`, not only `127.0.0.1:8088`.

### Sensors Do Not Start

Check status:

```bash
curl http://127.0.0.1:8088/api/status
```

Check USB devices:

```bash
v4l2-ctl --list-devices
ls /dev/ttyUSB*
```

Then update `ui_settings.json` device indexes/ports.
