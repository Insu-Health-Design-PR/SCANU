# Layer 8 `dev_adrian` Local Jetson Orin Demo

This guide is for running the current `dev_adrian` branch locally on the Jetson Orin before moving the frontend to Vercel or exposing the backend through Cloudflare.

Target machine:

```text
Host/user: insu@insu-desktop
Repo path: ~/Desktop/SCANU-dev_adrian
Software path: ~/Desktop/SCANU-dev_adrian/software
Layer 8 path: ~/Desktop/SCANU-dev_adrian/software/layer8_ui
```

Phase 1 goal:

```text
Run backend + frontend + sensors + cameras + Layer 4 model locally on the Jetson.
Confirm endpoints, WebSocket, system status, presence sensor, console log, RGB camera, thermal camera, and point cloud behavior before Vercel/Cloudflare.
```

## 1) Update The Repo

```bash
cd ~/Desktop/SCANU-dev_adrian
git fetch origin
git checkout dev_adrian
git pull origin dev_adrian
git branch --show-current
```

Expected branch:

```text
dev_adrian
```

## 2) Install Base System Packages

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

If virtual environment creation fails with `ensurepip is not available`, install the Python-version-specific venv package.

For Python 3.8:

```bash
sudo apt install -y python3.8-venv
```

For Python 3.10:

```bash
sudo apt install -y python3.10-venv
```

Check versions:

```bash
lsb_release -a
python3 --version
```

## 3) Install Node.js 20

The Layer 8 frontend uses Vite and needs a modern Node version.

Check current Node/npm:

```bash
node -v || true
npm -v || true
```

Install Node 20:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

If install fails because old Ubuntu Node packages conflict with NodeSource:

```bash
sudo apt remove -y nodejs npm libnode-dev libnode72 || true
sudo apt autoremove -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

Expected Node:

```text
v20.x.x
```

## 4) Create The Python Environment

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

If the venv was partially created and failed:

```bash
cd ~/Desktop/SCANU-dev_adrian/software
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

## 5) Install Python Dependencies

Keep the venv active:

```bash
cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
pip install -r layer8_ui/requirements.txt
pip install -r layer1_radar/requirements.txt
```

## 6) Install Layer 4 Model Dependencies Carefully

On Jetson, PyTorch and torchvision should match the NVIDIA JetPack image. Check first before forcing upgrades.

```bash
cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
python3 - <<'PY'
import torch
print("torch:", torch.__version__)
try:
    import torchvision
    print("torchvision:", torchvision.__version__)
except Exception as exc:
    print("torchvision import failed:", exc)
PY
```

If PyTorch and torchvision already work, install the remaining Layer 4 packages without forcing a torch replacement:

```bash
pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
```

Only run the full Layer 4 requirements if you are sure it will not break the NVIDIA PyTorch build:

```bash
pip install -r layer4_inference/requirements.txt
```

## 7) Install Frontend Dependencies

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
```

If `vite: not found` appears later, rerun:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
npx vite --version
```

## 8) Check Cameras And Sensors

Check camera devices:

```bash
v4l2-ctl --list-devices
```

Check USB/serial devices for radar or sensor hardware:

```bash
ls /dev/ttyUSB* 2>/dev/null || true
ls /dev/ttyACM* 2>/dev/null || true
```

If the user cannot access serial/camera devices, add the user to common hardware groups and reboot:

```bash
sudo usermod -aG dialout,video insu
sudo reboot
```

## 9) Run Backend + Frontend Locally

For Phase 1, run without `LAYER8_API_KEY`. This keeps local endpoints open for the frontend and verification scripts.

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
INSTALL_FRONTEND_DEPS=0 ./scripts/start_layer8_stack.sh
```

Expected services:

```text
Backend:  http://127.0.0.1:8088
Frontend: http://127.0.0.1:4173
```

Open on the Jetson:

```text
http://127.0.0.1:4173
```

If accessing from another machine through Tailscale, replace the IP with the Jetson Tailscale IP:

```text
http://100.92.1.128:4173
```

Backend through Tailscale:

```text
http://100.92.1.128:8088
```

## 10) Check Backend Endpoints

Open a second terminal:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
./scripts/check_layer8_backend.sh
```

Manual endpoint checks:

```bash
curl http://127.0.0.1:8088/api/health
curl http://127.0.0.1:8088/api/status
curl http://127.0.0.1:8088/api/visual/latest
curl http://127.0.0.1:8088/api/alerts/recent?limit=10
curl http://127.0.0.1:8088/api/layers/summary
```

Expected result:

```text
All endpoints return HTTP 200.
```

## 11) Start Sensors From Layer 8

```bash
curl -X POST http://127.0.0.1:8088/api/run_all
```

Then check status again:

```bash
curl http://127.0.0.1:8088/api/status
curl http://127.0.0.1:8088/api/visual/latest
curl http://127.0.0.1:8088/api/layers/summary
```

## 12) Run Integration Tests

Basic Layer 1-8 integration check:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
./scripts/verify_layer8_layers_integration.sh
```

Live Jetson check for frontend, backend, cameras, visuals, layers, and CORS:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
./scripts/verify_layer8_live_jetson.sh
```

Require non-empty point cloud data:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
REQUIRE_POINT_CLOUD=1 ./scripts/verify_layer8_live_jetson.sh
```

## 13) Logs

Backend log:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
tail -f logs/backend.dev.log
```

Frontend log:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
tail -f logs/frontend.dev.log
```

## 14) Common Fixes

### Frontend stops immediately with `vite: not found`

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
npx vite --version
```

Then restart:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
INSTALL_FRONTEND_DEPS=0 ./scripts/start_layer8_stack.sh
```

### Backend import fails with `No module named layer8_ui`

Run scripts from `software/layer8_ui`, not from the repo root:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
./scripts/start_layer8_stack.sh
```

### Port already in use

```bash
ss -ltnp | grep -E ':8088|:4173' || true
```

Stop the old process or reboot the Jetson.

### Camera not detected

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

If permission fails:

```bash
sudo usermod -aG video insu
sudo reboot
```

### Radar/serial permission denied

```bash
sudo usermod -aG dialout insu
sudo reboot
```

## 15) Phase 1 Pass Criteria

Phase 1 is ready when all of this works locally on the Jetson:

```text
Frontend opens at http://127.0.0.1:4173
Backend responds at http://127.0.0.1:8088/api/health
/api/status returns system state
/api/visual/latest returns RGB/thermal/point cloud data or clear live/fallback state
/api/layers/summary exposes Layer 1 through Layer 8
WebSocket /ws/events connects without repeated errors
RGB camera appears in the UI
Thermal camera appears in the UI if connected
Point cloud appears if radar/sensor pipeline is connected
Presence sensor/status updates
Console log receives events
Execution controls call backend endpoints
Layer 4 model imports and can run detection pipeline
```

## 16) Phase 2 Later: Vercel + Cloudflare

Do not start here until Phase 1 passes locally.

When ready, the backend can be started with API key protection and exposed through Cloudflare Tunnel:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
source ../.venv/bin/activate
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh
```

Then in another terminal:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_cloudflare_tunnel.sh
```

Vercel would then use:

```text
VITE_LAYER8_API_BASE=https://your-cloudflare-url
VITE_LAYER8_WS_URL=wss://your-cloudflare-url/ws/events
VITE_LAYER8_API_KEY=change-this-key
```
