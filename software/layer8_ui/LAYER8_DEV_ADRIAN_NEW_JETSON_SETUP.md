# Layer 8 `dev_adrian` New Jetson Setup

This guide is for a new Jetson that will run the current `dev_adrian` branch.

Use this guide when you want the newer Layer 8 backend that supports:

```text
Backend port: 8088
Vercel frontend: https://scanu-ui.vercel.app
API key support: LAYER8_API_KEY
Cloudflare Tunnel helper scripts
Modern frontend contract: /api/visual/latest, /api/health, /api/ui/preferences, /ws/events
```

This is different from `dev_kpr-layer8`, which is the older local demo branch.

## 1) Clone Or Update The Repo

Expected Jetson path:

```bash
~/Desktop/SCANU-dev_adrian
```

If the repo does not exist yet:

```bash
cd ~/Desktop
git clone https://github.com/Insu-Health-Design-PR/SCANU.git SCANU-dev_adrian
cd ~/Desktop/SCANU-dev_adrian
git checkout dev_adrian
```

If the repo already exists:

```bash
cd ~/Desktop/SCANU-dev_adrian
git fetch origin
git checkout dev_adrian
git pull origin dev_adrian
```

Confirm branch:

```bash
git branch --show-current
```

Expected:

```text
dev_adrian
```

## 2) Install System Packages

Check Ubuntu version:

```bash
lsb_release -a
python3 --version
```

Install base packages:

```bash
sudo apt update
sudo apt install -y \
  git \
  curl \
  ca-certificates \
  python3-pip \
  python3-venv \
  python3-dev \
  build-essential \
  v4l-utils \
  ffmpeg \
  libgl1 \
  libglib2.0-0
```

If `python3-venv` is not available on Ubuntu 20.04 / Python 3.8, use:

```bash
sudo apt install -y python3.8-venv
```

Check camera devices:

```bash
v4l2-ctl --list-devices
```

Check radar/mmWave serial ports:

```bash
ls /dev/ttyUSB*
```

## 3) Create Python Virtual Environment

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

If venv creation fails with `ensurepip is not available`, install the matching venv package:

```bash
sudo apt install -y python3-venv
# or on Python 3.8 systems:
sudo apt install -y python3.8-venv
```

Then recreate:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

## 4) Install Python Dependencies

From `software` with the venv active:

```bash
cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
pip install -r layer8_ui/requirements.txt
pip install -r layer1_radar/requirements.txt
```

For weapon AI / Layer 4:

```bash
pip install -r layer4_inference/requirements.txt
```

### Jetson PyTorch Warning

On Jetson, PyTorch and torchvision should match the JetPack/NVIDIA image. Do not blindly force generic desktop wheels if Jetson already has working NVIDIA builds.

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

If `torch` works and only `torchvision` warns, install the compatible torchvision for your torch/JetPack version instead of upgrading everything blindly.

## 5) Install Node.js For Local Frontend Testing

The frontend requires a modern Node version. Use Node 20.

```bash
node -v || true
npm -v || true
```

If Node is missing or too old:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

If install fails because old Ubuntu Node packages conflict with NodeSource, remove old packages first:

```bash
sudo apt remove -y nodejs npm libnode-dev libnode72 || true
sudo apt autoremove -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

Install frontend dependencies:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
```

## 6) Run Backend Only For Vercel

This is the recommended command when the backend runs on Jetson and the frontend is hosted at:

```text
https://scanu-ui.vercel.app
```

Run on the Jetson:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh
```

Backend default:

```text
http://127.0.0.1:8088
```

The script sets:

```text
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8088
LAYER8_CORS_ORIGINS=https://scanu-ui.vercel.app
```

## 7) Check Backend Locally

In a second terminal on the Jetson:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
LAYER8_API_KEY="change-this-key" ./scripts/check_layer8_backend.sh
```

Manual checks:

```bash
curl http://127.0.0.1:8088/api/health
curl -H "X-Layer8-Api-Key: change-this-key" http://127.0.0.1:8088/api/status
curl -H "X-Layer8-Api-Key: change-this-key" http://127.0.0.1:8088/api/visual/latest
```

Expected result:

```text
/api/health -> 200
/api/status -> 200 with API key
/api/visual/latest -> 200 with API key
```

## 8) Run Backend + Frontend Locally On Jetson

Use this if you want to test the frontend on the Jetson before relying on Vercel:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
INSTALL_FRONTEND_DEPS=1 ./scripts/start_layer8_stack.sh
```

Defaults:

```text
Backend:  http://127.0.0.1:8088
Frontend: http://127.0.0.1:4173
```

From another machine on the same network/Tailscale:

```text
http://<JETSON_IP>:4173
```

If your Jetson Tailscale IP is `100.92.1.128`:

```text
http://100.92.1.128:4173
```

## 9) Expose Backend To Vercel With Cloudflare Tunnel

In terminal 1, backend:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh
```

In terminal 2, tunnel:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_cloudflare_tunnel.sh
```

Cloudflare prints a public URL like:

```text
https://example.trycloudflare.com
```

Set these in Vercel:

```text
VITE_LAYER8_API_BASE=https://example.trycloudflare.com
VITE_LAYER8_WS_URL=wss://example.trycloudflare.com/ws/events
VITE_LAYER8_API_KEY=change-this-key
```

Then redeploy:

```text
https://scanu-ui.vercel.app
```

## 10) Verify Public Backend URL

After Cloudflare prints the tunnel URL:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
BACKEND_URL="https://example.trycloudflare.com" \
LAYER8_API_KEY="change-this-key" \
./scripts/check_layer8_backend.sh
```

## 11) Live Jetson Checks

Basic Layer 8 integration check:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
./scripts/verify_layer8_layers_integration.sh
```

Live hardware check:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
./scripts/verify_layer8_live_jetson.sh
```

Strict point-cloud check:

```bash
REQUIRE_POINT_CLOUD=1 ./scripts/verify_layer8_live_jetson.sh
```

Note: some older verification scripts may not send `LAYER8_API_KEY` headers. For the secured Vercel backend mode, prefer `check_layer8_backend.sh` first.

## 12) One-Shot Install Sequence

Use this on a fresh Jetson after cloning the repo:

```bash
cd ~/Desktop/SCANU-dev_adrian
git fetch origin
git checkout dev_adrian
git pull origin dev_adrian

sudo apt update
sudo apt install -y git curl ca-certificates python3-pip python3-venv python3-dev build-essential v4l-utils ffmpeg libgl1 libglib2.0-0

cd ~/Desktop/SCANU-dev_adrian/software
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip install -r layer8_ui/requirements.txt
pip install -r layer1_radar/requirements.txt
pip install -r layer4_inference/requirements.txt

cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install

cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh
```

## 13) Troubleshooting

### `python3 -m venv .venv` Fails

Install the matching venv package:

```bash
sudo apt install -y python3-venv
# or:
sudo apt install -y python3.8-venv
```

### `npm: command not found`

Install Node 20:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Node Install Fails With `libnode-dev` Conflict

```bash
sudo apt remove -y nodejs npm libnode-dev libnode72 || true
sudo apt autoremove -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Port 8088 Already In Use

```bash
lsof -i :8088
```

Stop the process or run on another port:

```bash
BACKEND_PORT=8089 LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh
```

### Cannot Reach Jetson From Another Device

Confirm backend is listening on all interfaces:

```bash
ss -ltnp | grep 8088
```

Expected:

```text
0.0.0.0:8088
```

Confirm Tailscale IP:

```bash
tailscale ip -4
```

Then test from your Mac:

```bash
curl http://100.92.1.128:8088/api/health
```

### Cameras Not Found

```bash
v4l2-ctl --list-devices
```

Then update camera indexes in:

```text
software/layer8_ui/ui_settings.json
```

### Radar Ports Not Found

```bash
ls /dev/ttyUSB*
```

Then update:

```text
mmwave.cli_port
mmwave.data_port
```

inside:

```text
software/layer8_ui/ui_settings.json
```
