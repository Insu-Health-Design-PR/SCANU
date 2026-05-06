# Layer 8 Jetson Runbook

This checkout serves the Layer 8 dashboard from `software/layer8_ui/static`.
There is no in-repo `software/layer8_ui/frontend` npm app.

## Jetson Setup For `dev_adrian`

Start from the project checkout on the Jetson:

```bash
cd ~/Desktop/SCANU
git fetch origin
git checkout dev_adrian
git pull origin dev_adrian
```

Install base system packages:

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

Create the project virtual environment:

```bash
cd ~/Desktop/SCANU/software
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
```

Install Layer dependencies:

```bash
pip install -r layer1_radar/requirements.txt
pip install -r layer8_ui/requirements.txt
pip install matplotlib
```

Check the Jetson PyTorch / torchvision state before installing AI packages:

```bash
python3 - <<'PY'
try:
    import torch
    print("torch OK:", torch.__version__)
    print("cuda:", torch.cuda.is_available())
except Exception as e:
    print("torch FAIL:", e)

try:
    import torchvision
    print("torchvision OK:", torchvision.__version__)
except Exception as e:
    print("torchvision FAIL:", e)
PY
```

Install the safe Layer 4 / AI subset without forcing generic PyTorch wheels:

```bash
pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
```

Avoid running this first on Jetson unless you already know your PyTorch wheels match your JetPack image:

```bash
pip install -r layer4_inference/requirements.txt
```

Set sensor permissions:

```bash
sudo usermod -aG dialout,video,plugdev $USER
```

Log out and back in after changing groups.

## Script Setup

The one-command setup path is:

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
| `Unable to evaluate type annotation 'dict[str, Any]'` on Python 3.8 | Install Layer 8 requirements again: `pip install -r ~/Desktop/SCANU/software/layer8_ui/requirements.txt`. This installs `eval-type-backport`. |
| `ModuleNotFoundError: layer8_ui` | Run commands from `software/layer8_ui` through `./scripts/layer8.sh`. |
| Port `8088` busy | `BACKEND_PORT=8089 ./scripts/layer8.sh start`. |
| Radar missing | Check `ls /dev/ttyUSB*` and `software/layer8_ui/ui_settings.json`. |
| Camera missing | Check `v4l2-ctl --list-devices`. |
