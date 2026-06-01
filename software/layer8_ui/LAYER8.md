# Layer 8 Jetson Runbook

This checkout serves the Layer 8 dashboard from `software/layer8_ui/static`.
There is no in-repo `software/layer8_ui/frontend` npm app.

## Setup On Jetson

```bash
cd ~/Desktop/SCANU-dev_adrian
git fetch origin
git checkout dev_adrian
git pull origin dev_adrian
```

```bash
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv python3-dev \
  build-essential cmake pkg-config \
  git curl wget \
  v4l-utils ffmpeg lsof jq \
  libgl1 libglib2.0-0 \
  libusb-1.0-0-dev libjpeg-dev zlib1g-dev libopenblas-dev
```

```bash
cd ~/Desktop/SCANU-dev_adrian/software
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip install -r layer1_sensor_hub/requirements.txt
pip install -r layer8_ui/requirements.txt
pip install matplotlib
pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
```

If Python 3.8 reports `Unable to evaluate type annotation 'dict[str, Any]'`, install:

```bash
pip install eval-type-backport
```

Set sensor permissions:

```bash
sudo usermod -aG dialout,video,plugdev $USER
```

Log out and back in after changing groups.

## Run The Designed Terminal Menu

Use this for the interactive SCANU control panel:

```bash
cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
python3 layer8_ui/scripts/run.py
```

The menu starts the Layer 8 backend, shows sensor status, and lets you:

- Start, stop, and restart all sensors
- Toggle mmWave, webcam, and thermal sensors
- Record a 30 second capture
- Export a JSON snapshot
- Watch live metrics
- View recent logs

Optional API key:

```bash
LAYER8_API_KEY="change-this-key" python3 layer8_ui/scripts/run.py
```

Open the dashboard at:

```text
http://<JETSON_IP>:8088
```

## Direct Script Commands

Use this when you do not need the menu:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/layer8.sh start
./scripts/layer8.sh check
./scripts/layer8.sh run-all
./scripts/layer8.sh stop-all
```

## Useful Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_HOST` | `0.0.0.0` | Bind host for uvicorn. |
| `BACKEND_PORT` | `8088` | Backend/UI port. |
| `LAYER8_API_KEY` | empty | Protect `/api/*` and WebSockets. |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ensurepip` / venv failure | `sudo apt install -y python3-venv python3-pip`, then recreate `.venv`. |
| `Unable to evaluate type annotation 'dict[str, Any]'` | `pip install eval-type-backport`. |
| `ModuleNotFoundError: layer8_ui` | Run from `~/Desktop/SCANU-dev_adrian/software`. |
| Port `8088` busy | `BACKEND_PORT=8089 python3 layer8_ui/scripts/run.py`. |
| Radar missing | Check `ls /dev/ttyUSB*` and `software/layer8_ui/ui_settings.json`. |
| Camera missing | Check `v4l2-ctl --list-devices`. |
