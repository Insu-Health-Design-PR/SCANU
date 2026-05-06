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
| `ModuleNotFoundError: layer8_ui` | Run commands from `software/layer8_ui` through `./scripts/layer8.sh`. |
| Port `8088` busy | `BACKEND_PORT=8089 ./scripts/layer8.sh start`. |
| Radar missing | Check `ls /dev/ttyUSB*` and `software/layer8_ui/ui_settings.json`. |
| Camera missing | Check `v4l2-ctl --list-devices`. |






xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ sudo apt update
[sudo] password for insu: 
1Sorry, try again.
[sudo] password for insu: 
Hit:1 https://repo.download.nvidia.com/jetson/common r35.4 InRelease
Hit:2 http://ports.ubuntu.com/ubuntu-ports focal InRelease
Get:3 https://pkgs.tailscale.com/stable/ubuntu focal InRelease                 
Get:4 http://ports.ubuntu.com/ubuntu-ports focal-updates InRelease [128 kB]    
Hit:5 https://repo.download.nvidia.com/jetson/t234 r35.4 InRelease
Get:6 http://ports.ubuntu.com/ubuntu-ports focal-backports InRelease [128 kB]
Get:7 http://ports.ubuntu.com/ubuntu-ports focal-security InRelease [128 kB]
Get:8 http://ports.ubuntu.com/ubuntu-ports focal-updates/main arm64 DEP-11 Metadata [276 kB]
Get:9 http://ports.ubuntu.com/ubuntu-ports focal-updates/universe arm64 DEP-11 Metadata [445 kB]
Get:10 http://ports.ubuntu.com/ubuntu-ports focal-backports/main arm64 DEP-11 Metadata [5,232 B]
Get:11 http://ports.ubuntu.com/ubuntu-ports focal-backports/universe arm64 DEP-11 Metadata [30.5 kB]
Get:12 http://ports.ubuntu.com/ubuntu-ports focal-security/main arm64 DEP-11 Metadata [74.7 kB]
Get:13 http://ports.ubuntu.com/ubuntu-ports focal-security/universe arm64 DEP-11 Metadata [159 kB]
Fetched 1,381 kB in 9s (156 kB/s)                                              
Reading package lists... Done
Building dependency tree       
Reading state information... Done
All packages are up to date.
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ cd ~/Desktop/SCANU-dev_adrian/software
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ rm -rf .venv
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ python3 -m venv .venv

insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ source .venv/bin/activate
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ python3 -m pip install --upgrade pip setuptools wheel
Collecting pip
  Downloading pip-25.0.1-py3-none-any.whl (1.8 MB)
     |████████████████████████████████| 1.8 MB 187 kB/s 
Collecting setuptools
  Downloading setuptools-75.3.4-py3-none-any.whl (1.3 MB)
     |████████████████████████████████| 1.3 MB 479 kB/s 
Collecting wheel
  Downloading wheel-0.45.1-py3-none-any.whl (72 kB)
     |████████████████████████████████| 72 kB 402 kB/s 
Installing collected packages: pip, setuptools, wheel
  Attempting uninstall: pip
    Found existing installation: pip 20.0.2
    Uninstalling pip-20.0.2:
      Successfully uninstalled pip-20.0.2
  Attempting uninstall: setuptools
    Found existing installation: setuptools 44.0.0
    Uninstalling setuptools-44.0.0:
      Successfully uninstalled setuptools-44.0.0
Successfully installed pip-25.0.1 setuptools-75.3.4 wheel-0.45.1
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ pip install -r layer1_radar/requirements.txt
Collecting pyserial>=3.5 (from -r layer1_radar/requirements.txt (line 5))
  Downloading pyserial-3.5-py2.py3-none-any.whl.metadata (1.6 kB)

Collecting numpy>=1.21.0 (from -r layer1_radar/requirements.txt (line 8))
  Downloading numpy-1.24.4-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (5.6 kB)
Downloading pyserial-3.5-py2.py3-none-any.whl (90 kB)
Downloading numpy-1.24.4-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.0/14.0 MB 2.7 MB/s eta 0:00:00
Installing collected packages: pyserial, numpy
Successfully installed numpy-1.24.4 pyserial-3.5
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ pip install -r layer8_ui/requirements.txt
Collecting fastapi>=0.109.0 (from -r layer8_ui/requirements.txt (line 1))
  Using cached fastapi-0.124.4-py3-none-any.whl.metadata (30 kB)
Collecting uvicorn>=0.27.0 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Using cached uvicorn-0.33.0-py3-none-any.whl.metadata (6.6 kB)
Collecting starlette<0.51.0,>=0.40.0 (from fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached starlette-0.44.0-py3-none-any.whl.metadata (6.3 kB)
Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached pydantic-2.10.6-py3-none-any.whl.metadata (30 kB)
Collecting typing-extensions>=4.8.0 (from fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Downloading typing_extensions-4.13.2-py3-none-any.whl.metadata (3.0 kB)
Collecting annotated-doc>=0.0.2 (from fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached annotated_doc-0.0.4-py3-none-any.whl.metadata (6.6 kB)
Collecting click>=7.0 (from uvicorn>=0.27.0->uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Using cached click-8.1.8-py3-none-any.whl.metadata (2.3 kB)
Collecting h11>=0.8 (from uvicorn>=0.27.0->uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting httptools>=0.6.3 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Downloading httptools-0.6.4-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (3.6 kB)
Collecting python-dotenv>=0.13 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Downloading python_dotenv-1.0.1-py3-none-any.whl.metadata (23 kB)
Collecting pyyaml>=5.1 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Downloading PyYAML-6.0.3-cp38-cp38-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (2.1 kB)
Collecting uvloop!=0.15.0,!=0.15.1,>=0.14.0 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Downloading uvloop-0.22.1-cp38-cp38-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (4.9 kB)
Collecting watchfiles>=0.13 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Downloading watchfiles-0.24.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.9 kB)
Collecting websockets>=10.4 (from uvicorn[standard]>=0.27.0->-r layer8_ui/requirements.txt (line 2))
  Using cached websockets-13.1-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.8 kB)
Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.27.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached pydantic_core-2.27.2-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.6 kB)
Collecting anyio<5,>=3.4.0 (from starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached anyio-4.5.2-py3-none-any.whl.metadata (4.7 kB)
Collecting idna>=2.8 (from anyio<5,>=3.4.0->starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Downloading idna-3.13-py3-none-any.whl.metadata (8.0 kB)
Collecting sniffio>=1.1 (from anyio<5,>=3.4.0->starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached sniffio-1.3.1-py3-none-any.whl.metadata (3.9 kB)
Collecting exceptiongroup>=1.0.2 (from anyio<5,>=3.4.0->starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r layer8_ui/requirements.txt (line 1))
  Using cached exceptiongroup-1.3.1-py3-none-any.whl.metadata (6.7 kB)
Using cached fastapi-0.124.4-py3-none-any.whl (113 kB)
Using cached uvicorn-0.33.0-py3-none-any.whl (62 kB)
Using cached annotated_doc-0.0.4-py3-none-any.whl (5.3 kB)
Using cached click-8.1.8-py3-none-any.whl (98 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Downloading httptools-0.6.4-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (455 kB)
Using cached pydantic-2.10.6-py3-none-any.whl (431 kB)
Using cached pydantic_core-2.27.2-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.8 MB)
Downloading python_dotenv-1.0.1-py3-none-any.whl (19 kB)
Downloading PyYAML-6.0.3-cp38-cp38-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (795 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 795.1/795.1 kB 9.6 MB/s eta 0:00:00
Using cached starlette-0.44.0-py3-none-any.whl (73 kB)
Downloading typing_extensions-4.13.2-py3-none-any.whl (45 kB)
Downloading uvloop-0.22.1-cp38-cp38-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (4.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.2/4.2 MB 8.6 MB/s eta 0:00:00
Downloading watchfiles-0.24.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (439 kB)
Using cached websockets-13.1-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (164 kB)
Using cached annotated_types-0.7.0-py3-none-any.whl (13 kB)
Using cached anyio-4.5.2-py3-none-any.whl (89 kB)
Using cached exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Downloading idna-3.13-py3-none-any.whl (68 kB)
Using cached sniffio-1.3.1-py3-none-any.whl (10 kB)
Installing collected packages: websockets, uvloop, typing-extensions, sniffio, pyyaml, python-dotenv, idna, httptools, h11, click, annotated-doc, uvicorn, pydantic-core, exceptiongroup, annotated-types, pydantic, anyio, watchfiles, starlette, fastapi
Successfully installed annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.5.2 click-8.1.8 exceptiongroup-1.3.1 fastapi-0.124.4 h11-0.16.0 httptools-0.6.4 idna-3.13 pydantic-2.10.6 pydantic-core-2.27.2 python-dotenv-1.0.1 pyyaml-6.0.3 sniffio-1.3.1 starlette-0.44.0 typing-extensions-4.13.2 uvicorn-0.33.0 uvloop-0.22.1 watchfiles-0.24.0 websockets-13.1
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ pip install matplotlib
Collecting matplotlib
  Downloading matplotlib-3.7.5-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (5.7 kB)
Collecting contourpy>=1.0.1 (from matplotlib)
  Downloading contourpy-1.1.1-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (5.9 kB)
Collecting cycler>=0.10 (from matplotlib)
  Downloading cycler-0.12.1-py3-none-any.whl.metadata (3.8 kB)
Collecting fonttools>=4.22.0 (from matplotlib)
  Downloading fonttools-4.57.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (102 kB)
Collecting kiwisolver>=1.0.1 (from matplotlib)
  Downloading kiwisolver-1.4.7-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (6.3 kB)
Requirement already satisfied: numpy<2,>=1.20 in ./.venv/lib/python3.8/site-packages (from matplotlib) (1.24.4)
Collecting packaging>=20.0 (from matplotlib)
  Downloading packaging-26.2-py3-none-any.whl.metadata (3.5 kB)
Collecting pillow>=6.2.0 (from matplotlib)
  Downloading pillow-10.4.0-cp38-cp38-manylinux_2_28_aarch64.whl.metadata (9.2 kB)
Collecting pyparsing>=2.3.1 (from matplotlib)
  Downloading pyparsing-3.1.4-py3-none-any.whl.metadata (5.1 kB)
Collecting python-dateutil>=2.7 (from matplotlib)
  Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl.metadata (8.4 kB)
Collecting importlib-resources>=3.2.0 (from matplotlib)
  Downloading importlib_resources-6.4.5-py3-none-any.whl.metadata (4.0 kB)
Collecting zipp>=3.1.0 (from importlib-resources>=3.2.0->matplotlib)
  Downloading zipp-3.20.2-py3-none-any.whl.metadata (3.7 kB)
Collecting six>=1.5 (from python-dateutil>=2.7->matplotlib)
  Downloading six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)
Downloading matplotlib-3.7.5-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (11.4 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.4/11.4 MB 10.0 MB/s eta 0:00:00
Downloading contourpy-1.1.1-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (285 kB)
Downloading cycler-0.12.1-py3-none-any.whl (8.3 kB)
Downloading fonttools-4.57.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (4.6 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.6/4.6 MB 1.7 MB/s eta 0:00:00
Downloading importlib_resources-6.4.5-py3-none-any.whl (36 kB)
Downloading kiwisolver-1.4.7-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.4 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.4/1.4 MB 3.2 MB/s eta 0:00:00
Downloading packaging-26.2-py3-none-any.whl (100 kB)
Downloading pillow-10.4.0-cp38-cp38-manylinux_2_28_aarch64.whl (4.4 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.4/4.4 MB 3.6 MB/s eta 0:00:00
Downloading pyparsing-3.1.4-py3-none-any.whl (104 kB)
Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Downloading six-1.17.0-py2.py3-none-any.whl (11 kB)
Downloading zipp-3.20.2-py3-none-any.whl (9.2 kB)
Installing collected packages: zipp, six, pyparsing, pillow, packaging, kiwisolver, fonttools, cycler, contourpy, python-dateutil, importlib-resources, matplotlib
Successfully installed contourpy-1.1.1 cycler-0.12.1 fonttools-4.57.0 importlib-resources-6.4.5 kiwisolver-1.4.7 matplotlib-3.7.5 packaging-26.2 pillow-10.4.0 pyparsing-3.1.4 python-dateutil-2.9.0.post0 six-1.17.0 zipp-3.20.2
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ python3 - <<'PY'
> try:
>     import torch
>     print("torch OK:", torch.__version__)
>     print("cuda:", torch.cuda.is_available())
> except Exception as e:
>     print("torch FAIL:", e)
> 
> try:
>     import torchvision
>     print("torchvision OK:", torchvision.__version__)
> except Exception as e:
>     print("torchvision FAIL:", e)
> PY
torch FAIL: No module named 'torch'
torchvision FAIL: No module named 'torchvision'
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
Collecting opencv-python-headless
  Downloading opencv_python_headless-4.13.0.92-cp37-abi3-manylinux_2_28_aarch64.whl.metadata (19 kB)
Requirement already satisfied: numpy in ./.venv/lib/python3.8/site-packages (1.24.4)
Collecting tqdm
  Downloading tqdm-4.67.3-py3-none-any.whl.metadata (57 kB)
Collecting scikit-learn
  Downloading scikit_learn-1.3.2-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (11 kB)
Collecting onnx
  Downloading onnx-1.17.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (16 kB)
Collecting ultralytics
  Downloading ultralytics-8.4.47-py3-none-any.whl.metadata (39 kB)
Requirement already satisfied: PyYAML in ./.venv/lib/python3.8/site-packages (6.0.3)
Collecting scipy>=1.5.0 (from scikit-learn)
  Downloading scipy-1.10.1-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (58 kB)
Collecting joblib>=1.1.1 (from scikit-learn)
  Downloading joblib-1.4.2-py3-none-any.whl.metadata (5.4 kB)
Collecting threadpoolctl>=2.0.0 (from scikit-learn)
  Downloading threadpoolctl-3.5.0-py3-none-any.whl.metadata (13 kB)
Collecting protobuf>=3.20.2 (from onnx)
  Downloading protobuf-5.29.6-cp38-abi3-manylinux2014_aarch64.whl.metadata (592 bytes)
Requirement already satisfied: matplotlib>=3.3.0 in ./.venv/lib/python3.8/site-packages (from ultralytics) (3.7.5)
Collecting opencv-python>=4.6.0 (from ultralytics)
  Downloading opencv_python-4.13.0.92-cp37-abi3-manylinux_2_28_aarch64.whl.metadata (19 kB)
Requirement already satisfied: pillow>=7.1.2 in ./.venv/lib/python3.8/site-packages (from ultralytics) (10.4.0)
Collecting requests>=2.23.0 (from ultralytics)
  Downloading requests-2.32.4-py3-none-any.whl.metadata (4.9 kB)
Collecting torch>=1.8.0 (from ultralytics)
  Downloading torch-2.4.1-cp38-cp38-manylinux2014_aarch64.whl.metadata (26 kB)
Collecting torchvision>=0.9.0 (from ultralytics)
  Downloading torchvision-0.19.1-cp38-cp38-manylinux2014_aarch64.whl.metadata (6.0 kB)
Collecting psutil>=5.8.0 (from ultralytics)
  Downloading psutil-7.2.2-cp36-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (22 kB)
Collecting polars>=0.20.0 (from ultralytics)
  Downloading polars-1.8.2-cp38-abi3-manylinux_2_24_aarch64.whl.metadata (14 kB)
Collecting ultralytics-thop>=2.0.18 (from ultralytics)
  Downloading ultralytics_thop-2.0.19-py3-none-any.whl.metadata (14 kB)
Requirement already satisfied: contourpy>=1.0.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (1.1.1)
Requirement already satisfied: cycler>=0.10 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (0.12.1)
Requirement already satisfied: fonttools>=4.22.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (4.57.0)
Requirement already satisfied: kiwisolver>=1.0.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (1.4.7)
Requirement already satisfied: packaging>=20.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (26.2)
Requirement already satisfied: pyparsing>=2.3.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (3.1.4)
Requirement already satisfied: python-dateutil>=2.7 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (2.9.0.post0)
Requirement already satisfied: importlib-resources>=3.2.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (6.4.5)
Collecting charset_normalizer<4,>=2 (from requests>=2.23.0->ultralytics)
  Downloading charset_normalizer-3.4.7-cp38-cp38-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (40 kB)
Requirement already satisfied: idna<4,>=2.5 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics) (3.13)
Collecting urllib3<3,>=1.21.1 (from requests>=2.23.0->ultralytics)
  Downloading urllib3-2.2.3-py3-none-any.whl.metadata (6.5 kB)
Collecting certifi>=2017.4.17 (from requests>=2.23.0->ultralytics)
  Downloading certifi-2026.4.22-py3-none-any.whl.metadata (2.5 kB)
Collecting filelock (from torch>=1.8.0->ultralytics)
  Downloading filelock-3.16.1-py3-none-any.whl.metadata (2.9 kB)
Requirement already satisfied: typing-extensions>=4.8.0 in ./.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (4.13.2)
Collecting sympy (from torch>=1.8.0->ultralytics)
  Downloading sympy-1.13.3-py3-none-any.whl.metadata (12 kB)
Collecting networkx (from torch>=1.8.0->ultralytics)
  Downloading networkx-3.1-py3-none-any.whl.metadata (5.3 kB)
Collecting jinja2 (from torch>=1.8.0->ultralytics)
  Downloading jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
Collecting fsspec (from torch>=1.8.0->ultralytics)
  Downloading fsspec-2025.3.0-py3-none-any.whl.metadata (11 kB)
Requirement already satisfied: zipp>=3.1.0 in ./.venv/lib/python3.8/site-packages (from importlib-resources>=3.2.0->matplotlib>=3.3.0->ultralytics) (3.20.2)
Requirement already satisfied: six>=1.5 in ./.venv/lib/python3.8/site-packages (from python-dateutil>=2.7->matplotlib>=3.3.0->ultralytics) (1.17.0)
Collecting MarkupSafe>=2.0 (from jinja2->torch>=1.8.0->ultralytics)
  Downloading MarkupSafe-2.1.5-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (3.0 kB)
Collecting mpmath<1.4,>=1.1.0 (from sympy->torch>=1.8.0->ultralytics)
  Downloading mpmath-1.3.0-py3-none-any.whl.metadata (8.6 kB)
Downloading opencv_python_headless-4.13.0.92-cp37-abi3-manylinux_2_28_aarch64.whl (35.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 35.0/35.0 MB 24.5 MB/s eta 0:00:00
Downloading tqdm-4.67.3-py3-none-any.whl (78 kB)
Downloading scikit_learn-1.3.2-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (10.5 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.5/10.5 MB 24.7 MB/s eta 0:00:00
Downloading onnx-1.17.0-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (15.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 15.9/15.9 MB 22.7 MB/s eta 0:00:00
Downloading ultralytics-8.4.47-py3-none-any.whl (1.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 17.7 MB/s eta 0:00:00
Downloading joblib-1.4.2-py3-none-any.whl (301 kB)
Downloading opencv_python-4.13.0.92-cp37-abi3-manylinux_2_28_aarch64.whl (46.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 46.7/46.7 MB 26.8 MB/s eta 0:00:00
Downloading polars-1.8.2-cp38-abi3-manylinux_2_24_aarch64.whl (29.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 29.2/29.2 MB 26.3 MB/s eta 0:00:00
Downloading protobuf-5.29.6-cp38-abi3-manylinux2014_aarch64.whl (320 kB)
Downloading psutil-7.2.2-cp36-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (156 kB)
Downloading requests-2.32.4-py3-none-any.whl (64 kB)
Downloading scipy-1.10.1-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (31.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 31.0/31.0 MB 26.5 MB/s eta 0:00:00
Downloading threadpoolctl-3.5.0-py3-none-any.whl (18 kB)
Downloading torch-2.4.1-cp38-cp38-manylinux2014_aarch64.whl (89.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 89.7/89.7 MB 27.1 MB/s eta 0:00:00
Downloading torchvision-0.19.1-cp38-cp38-manylinux2014_aarch64.whl (14.1 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.1/14.1 MB 25.7 MB/s eta 0:00:00
Downloading ultralytics_thop-2.0.19-py3-none-any.whl (28 kB)
Downloading certifi-2026.4.22-py3-none-any.whl (135 kB)
Downloading charset_normalizer-3.4.7-cp38-cp38-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (192 kB)
Downloading urllib3-2.2.3-py3-none-any.whl (126 kB)
Downloading filelock-3.16.1-py3-none-any.whl (16 kB)
Downloading fsspec-2025.3.0-py3-none-any.whl (193 kB)
Downloading jinja2-3.1.6-py3-none-any.whl (134 kB)
Downloading networkx-3.1-py3-none-any.whl (2.1 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 21.3 MB/s eta 0:00:00
Downloading sympy-1.13.3-py3-none-any.whl (6.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.2/6.2 MB 24.4 MB/s eta 0:00:00
Downloading MarkupSafe-2.1.5-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (26 kB)
Downloading mpmath-1.3.0-py3-none-any.whl (536 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 536.2/536.2 kB 10.1 MB/s eta 0:00:00
Installing collected packages: mpmath, urllib3, tqdm, threadpoolctl, sympy, scipy, psutil, protobuf, polars, opencv-python-headless, opencv-python, networkx, MarkupSafe, joblib, fsspec, filelock, charset_normalizer, certifi, scikit-learn, requests, onnx, jinja2, torch, ultralytics-thop, torchvision, ultralytics
Successfully installed MarkupSafe-2.1.5 certifi-2026.4.22 charset_normalizer-3.4.7 filelock-3.16.1 fsspec-2025.3.0 jinja2-3.1.6 joblib-1.4.2 mpmath-1.3.0 networkx-3.1 onnx-1.17.0 opencv-python-4.13.0.92 opencv-python-headless-4.13.0.92 polars-1.8.2 protobuf-5.29.6 psutil-7.2.2 requests-2.32.4 scikit-learn-1.3.2 scipy-1.10.1 sympy-1.13.3 threadpoolctl-3.5.0 torch-2.4.1 torchvision-0.19.1 tqdm-4.67.3 ultralytics-8.4.47 ultralytics-thop-2.0.19 urllib3-2.2.3
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ pip install -r layer4_inference/requirements.txt
Requirement already satisfied: torch>=2.1.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 2)) (2.4.1)
Requirement already satisfied: torchvision>=0.16.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 3)) (0.19.1)
Requirement already satisfied: opencv-python-headless>=4.8.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 4)) (4.13.0.92)
Requirement already satisfied: numpy>=1.24.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 5)) (1.24.4)
Requirement already satisfied: tqdm>=4.66.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 6)) (4.67.3)
Requirement already satisfied: scikit-learn>=1.3.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 7)) (1.3.2)
Requirement already satisfied: onnx>=1.16.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 8)) (1.17.0)
Requirement already satisfied: ultralytics>=8.3.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 9)) (8.4.47)
Requirement already satisfied: PyYAML>=6.0.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 10)) (6.0.3)
Requirement already satisfied: filelock in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (3.16.1)
Requirement already satisfied: typing-extensions>=4.8.0 in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (4.13.2)
Requirement already satisfied: sympy in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (1.13.3)
Requirement already satisfied: networkx in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (3.1)
Requirement already satisfied: jinja2 in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (3.1.6)
Requirement already satisfied: fsspec in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (2025.3.0)
Requirement already satisfied: pillow!=8.3.*,>=5.3.0 in ./.venv/lib/python3.8/site-packages (from torchvision>=0.16.0->-r layer4_inference/requirements.txt (line 3)) (10.4.0)
Requirement already satisfied: scipy>=1.5.0 in ./.venv/lib/python3.8/site-packages (from scikit-learn>=1.3.0->-r layer4_inference/requirements.txt (line 7)) (1.10.1)
Requirement already satisfied: joblib>=1.1.1 in ./.venv/lib/python3.8/site-packages (from scikit-learn>=1.3.0->-r layer4_inference/requirements.txt (line 7)) (1.4.2)
Requirement already satisfied: threadpoolctl>=2.0.0 in ./.venv/lib/python3.8/site-packages (from scikit-learn>=1.3.0->-r layer4_inference/requirements.txt (line 7)) (3.5.0)
Requirement already satisfied: protobuf>=3.20.2 in ./.venv/lib/python3.8/site-packages (from onnx>=1.16.0->-r layer4_inference/requirements.txt (line 8)) (5.29.6)
Requirement already satisfied: matplotlib>=3.3.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.7.5)
Requirement already satisfied: opencv-python>=4.6.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (4.13.0.92)
Requirement already satisfied: requests>=2.23.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.32.4)
Requirement already satisfied: psutil>=5.8.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (7.2.2)
Requirement already satisfied: polars>=0.20.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.8.2)
Requirement already satisfied: ultralytics-thop>=2.0.18 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.0.19)
Requirement already satisfied: contourpy>=1.0.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.1.1)
Requirement already satisfied: cycler>=0.10 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (0.12.1)
Requirement already satisfied: fonttools>=4.22.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (4.57.0)
Requirement already satisfied: kiwisolver>=1.0.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.4.7)
Requirement already satisfied: packaging>=20.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (26.2)
Requirement already satisfied: pyparsing>=2.3.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.1.4)
Requirement already satisfied: python-dateutil>=2.7 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.9.0.post0)
Requirement already satisfied: importlib-resources>=3.2.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (6.4.5)
Requirement already satisfied: charset_normalizer<4,>=2 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.4.7)
Requirement already satisfied: idna<4,>=2.5 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.13)
Requirement already satisfied: urllib3<3,>=1.21.1 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.2.3)
Requirement already satisfied: certifi>=2017.4.17 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2026.4.22)
Requirement already satisfied: MarkupSafe>=2.0 in ./.venv/lib/python3.8/site-packages (from jinja2->torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (2.1.5)
Requirement already satisfied: mpmath<1.4,>=1.1.0 in ./.venv/lib/python3.8/site-packages (from sympy->torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (1.3.0)
Requirement already satisfied: zipp>=3.1.0 in ./.venv/lib/python3.8/site-packages (from importlib-resources>=3.2.0->matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.20.2)
Requirement already satisfied: six>=1.5 in ./.venv/lib/python3.8/site-packages (from python-dateutil>=2.7->matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.17.0)
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ pip install -r layer4_inference/requirements.txt
Requirement already satisfied: torch>=2.1.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 2)) (2.4.1)
Requirement already satisfied: torchvision>=0.16.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 3)) (0.19.1)
Requirement already satisfied: opencv-python-headless>=4.8.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 4)) (4.13.0.92)
Requirement already satisfied: numpy>=1.24.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 5)) (1.24.4)
Requirement already satisfied: tqdm>=4.66.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 6)) (4.67.3)
Requirement already satisfied: scikit-learn>=1.3.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 7)) (1.3.2)
Requirement already satisfied: onnx>=1.16.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 8)) (1.17.0)
Requirement already satisfied: ultralytics>=8.3.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 9)) (8.4.47)
Requirement already satisfied: PyYAML>=6.0.0 in ./.venv/lib/python3.8/site-packages (from -r layer4_inference/requirements.txt (line 10)) (6.0.3)
Requirement already satisfied: filelock in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (3.16.1)
Requirement already satisfied: typing-extensions>=4.8.0 in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (4.13.2)
Requirement already satisfied: sympy in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (1.13.3)
Requirement already satisfied: networkx in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (3.1)
Requirement already satisfied: jinja2 in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (3.1.6)
Requirement already satisfied: fsspec in ./.venv/lib/python3.8/site-packages (from torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (2025.3.0)
Requirement already satisfied: pillow!=8.3.*,>=5.3.0 in ./.venv/lib/python3.8/site-packages (from torchvision>=0.16.0->-r layer4_inference/requirements.txt (line 3)) (10.4.0)
Requirement already satisfied: scipy>=1.5.0 in ./.venv/lib/python3.8/site-packages (from scikit-learn>=1.3.0->-r layer4_inference/requirements.txt (line 7)) (1.10.1)
Requirement already satisfied: joblib>=1.1.1 in ./.venv/lib/python3.8/site-packages (from scikit-learn>=1.3.0->-r layer4_inference/requirements.txt (line 7)) (1.4.2)
Requirement already satisfied: threadpoolctl>=2.0.0 in ./.venv/lib/python3.8/site-packages (from scikit-learn>=1.3.0->-r layer4_inference/requirements.txt (line 7)) (3.5.0)
Requirement already satisfied: protobuf>=3.20.2 in ./.venv/lib/python3.8/site-packages (from onnx>=1.16.0->-r layer4_inference/requirements.txt (line 8)) (5.29.6)
Requirement already satisfied: matplotlib>=3.3.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.7.5)
Requirement already satisfied: opencv-python>=4.6.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (4.13.0.92)
Requirement already satisfied: requests>=2.23.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.32.4)
Requirement already satisfied: psutil>=5.8.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (7.2.2)
Requirement already satisfied: polars>=0.20.0 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.8.2)
Requirement already satisfied: ultralytics-thop>=2.0.18 in ./.venv/lib/python3.8/site-packages (from ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.0.19)
Requirement already satisfied: contourpy>=1.0.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.1.1)
Requirement already satisfied: cycler>=0.10 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (0.12.1)
Requirement already satisfied: fonttools>=4.22.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (4.57.0)
Requirement already satisfied: kiwisolver>=1.0.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.4.7)
Requirement already satisfied: packaging>=20.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (26.2)
Requirement already satisfied: pyparsing>=2.3.1 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.1.4)
Requirement already satisfied: python-dateutil>=2.7 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.9.0.post0)
Requirement already satisfied: importlib-resources>=3.2.0 in ./.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (6.4.5)
Requirement already satisfied: charset_normalizer<4,>=2 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.4.7)
Requirement already satisfied: idna<4,>=2.5 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.13)
Requirement already satisfied: urllib3<3,>=1.21.1 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2.2.3)
Requirement already satisfied: certifi>=2017.4.17 in ./.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (2026.4.22)
Requirement already satisfied: MarkupSafe>=2.0 in ./.venv/lib/python3.8/site-packages (from jinja2->torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (2.1.5)
Requirement already satisfied: mpmath<1.4,>=1.1.0 in ./.venv/lib/python3.8/site-packages (from sympy->torch>=2.1.0->-r layer4_inference/requirements.txt (line 2)) (1.3.0)
Requirement already satisfied: zipp>=3.1.0 in ./.venv/lib/python3.8/site-packages (from importlib-resources>=3.2.0->matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (3.20.2)
Requirement already satisfied: six>=1.5 in ./.venv/lib/python3.8/site-packages (from python-dateutil>=2.7->matplotlib>=3.3.0->ultralytics>=8.3.0->-r layer4_inference/requirements.txt (line 9)) (1.17.0)
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ sudo usermod -aG dialout,video,plugdev $USER
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ INSTALL_SYSTEM_DEPS=1 ./scripts/layer8.sh setup
[setup] software dir: /home/insu/Desktop/SCANU-dev_adrian/software
[setup] layer8 dir  : /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui
[setup] venv dir    : /home/insu/Desktop/SCANU-dev_adrian/software/.venv
Hit:1 https://repo.download.nvidia.com/jetson/common r35.4 InRelease
Hit:2 http://ports.ubuntu.com/ubuntu-ports focal InRelease
Get:3 https://pkgs.tailscale.com/stable/ubuntu focal InRelease                 
Hit:4 http://ports.ubuntu.com/ubuntu-ports focal-updates InRelease             
Hit:5 https://repo.download.nvidia.com/jetson/t234 r35.4 InRelease             
Hit:6 http://ports.ubuntu.com/ubuntu-ports focal-backports InRelease
Hit:7 http://ports.ubuntu.com/ubuntu-ports focal-security InRelease
Fetched 6,581 B in 1s (4,868 B/s)
Reading package lists... Done
Building dependency tree       
Reading state information... Done
All packages are up to date.
Reading package lists... Done
Building dependency tree       
Reading state information... Done
python3-dev is already the newest version (3.8.2-0ubuntu2).
python3-venv is already the newest version (3.8.2-0ubuntu2).
v4l-utils is already the newest version (1.18.0-2build1).
build-essential is already the newest version (12.8ubuntu1.1).
build-essential set to manually installed.
ca-certificates is already the newest version (20240203~20.04.1).
ca-certificates set to manually installed.
curl is already the newest version (7.68.0-1ubuntu2.25).
git is already the newest version (1:2.25.1-1ubuntu3.14).
libgl1 is already the newest version (1.3.2-1~ubuntu0.20.04.2).
libglib2.0-0 is already the newest version (2.64.6-1~ubuntu20.04.9).
ffmpeg is already the newest version (7:4.2.7-0ubuntu0.1).
The following packages were automatically installed and are no longer required:
  apt-clone archdetect-deb bogl-bterm busybox-static cryptsetup-bin
  dctrl-tools dpkg-repack gdal-data gir1.2-goa-1.0 gir1.2-timezonemap-1.0
  gir1.2-xkl-1.0 grub-common libaec0 libarmadillo9 libarpack2 libavcodec-dev
  libavformat-dev libavresample-dev libavutil-dev libcfitsio8 libcharls2
  libdap25 libdapclient6v5 libdc1394-22-dev libdebian-installer4 libepsilon1
  libevent-core-2.1-7 libevent-pthreads-2.1-7 libexif-dev libfreexl1
  libfwupdplugin1 libfyba0 libgdal26 libgdcm-dev libgdcm3.0 libgeos-3.8.0
  libgeos-c1v5 libgeotiff5 libgl2ps1.4 libgphoto2-dev libhdf4-0-alt
  libhdf5-103 libhdf5-openmpi-103 libhwloc-plugins libhwloc15 libilmbase-dev
  libjbig-dev libjsoncpp1 libkmlbase1 libkmldom1 libkmlengine1 liblept5
  liblzma-dev libminizip1 libnetcdf-c++4 libnetcdf15 libodbc1 libogdi4.1
  libopencv-calib3d4.2 libopencv-contrib4.2 libopencv-dnn4.2
  libopencv-features2d4.2 libopencv-flann4.2 libopencv-highgui4.2
  libopencv-imgcodecs4.2 libopencv-imgproc4.2 libopencv-ml4.2
  libopencv-objdetect4.2 libopencv-photo4.2 libopencv-shape4.2
  libopencv-stitching4.2 libopencv-superres4.2 libopencv-video4.2
  libopencv-videoio4.2 libopencv-videostab4.2 libopencv-viz4.2
  libopencv4.2-java libopencv4.2-jni libopenexr-dev libopenmpi3 libpmix2
  libpng-dev libpq5 libproj15 libqhull7 libraw1394-dev libsocket++1
  libspatialite7 libsuperlu5 libswresample-dev libswscale-dev libsz2
  libtbb-dev libtesseract4 libtiff-dev libtiffxx5 libtimezonemap-data
  libtimezonemap1 liburiparser1 libvtk6.3 libxerces-c3.2 libxmlb1 libxnvctrl0
  odbcinst odbcinst1debian2 os-prober proj-data python3-icu python3-pam rdate
  tasksel tasksel-data
Use 'sudo apt autoremove' to remove them.
The following additional packages will be installed:
  python3-setuptools python3-wheel
Suggested packages:
  python-setuptools-doc
The following NEW packages will be installed:
  python3-pip python3-setuptools python3-wheel
0 upgraded, 3 newly installed, 0 to remove and 0 not upgraded.
Need to get 585 kB of archives.
After this operation, 2,623 kB of additional disk space will be used.
Get:1 http://ports.ubuntu.com/ubuntu-ports focal-updates/main arm64 python3-setuptools all 45.2.0-1ubuntu0.3 [330 kB]
Get:2 http://ports.ubuntu.com/ubuntu-ports focal-updates/universe arm64 python3-wheel all 0.34.2-1ubuntu0.1 [23.9 kB]
Get:3 http://ports.ubuntu.com/ubuntu-ports focal-updates/universe arm64 python3-pip all 20.0.2-5ubuntu1.11 [231 kB]
Fetched 585 kB in 2s (376 kB/s)          
debconf: delaying package configuration, since apt-utils is not installed
Selecting previously unselected package python3-setuptools.
(Reading database ... 157693 files and directories currently installed.)
Preparing to unpack .../python3-setuptools_45.2.0-1ubuntu0.3_all.deb ...
Unpacking python3-setuptools (45.2.0-1ubuntu0.3) ...
Selecting previously unselected package python3-wheel.
Preparing to unpack .../python3-wheel_0.34.2-1ubuntu0.1_all.deb ...
Unpacking python3-wheel (0.34.2-1ubuntu0.1) ...
Selecting previously unselected package python3-pip.
Preparing to unpack .../python3-pip_20.0.2-5ubuntu1.11_all.deb ...
Unpacking python3-pip (20.0.2-5ubuntu1.11) ...
Setting up python3-setuptools (45.2.0-1ubuntu0.3) ...
Setting up python3-wheel (0.34.2-1ubuntu0.1) ...
Setting up python3-pip (20.0.2-5ubuntu1.11) ...
Processing triggers for man-db (2.9.1-1) ...
Requirement already satisfied: pip in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (25.0.1)
Requirement already satisfied: setuptools in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (75.3.4)
Requirement already satisfied: wheel in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (0.45.1)
Requirement already satisfied: fastapi>=0.109.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from -r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (0.124.4)
Requirement already satisfied: uvicorn>=0.27.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (0.33.0)
Requirement already satisfied: starlette<0.51.0,>=0.40.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (0.44.0)
Requirement already satisfied: pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (2.10.6)
Requirement already satisfied: typing-extensions>=4.8.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (4.13.2)
Requirement already satisfied: annotated-doc>=0.0.2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (0.0.4)
Requirement already satisfied: click>=7.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn>=0.27.0->uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (8.1.8)
Requirement already satisfied: h11>=0.8 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn>=0.27.0->uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (0.16.0)
Requirement already satisfied: httptools>=0.6.3 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (0.6.4)
Requirement already satisfied: python-dotenv>=0.13 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (1.0.1)
Requirement already satisfied: pyyaml>=5.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (6.0.3)
Requirement already satisfied: uvloop!=0.15.0,!=0.15.1,>=0.14.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (0.22.1)
Requirement already satisfied: watchfiles>=0.13 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (0.24.0)
Requirement already satisfied: websockets>=10.4 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from uvicorn[standard]>=0.27.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 2)) (13.1)
Requirement already satisfied: annotated-types>=0.6.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (0.7.0)
Requirement already satisfied: pydantic-core==2.27.2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (2.27.2)
Requirement already satisfied: anyio<5,>=3.4.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (4.5.2)
Requirement already satisfied: idna>=2.8 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from anyio<5,>=3.4.0->starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (3.13)
Requirement already satisfied: sniffio>=1.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from anyio<5,>=3.4.0->starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (1.3.1)
Requirement already satisfied: exceptiongroup>=1.0.2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from anyio<5,>=3.4.0->starlette<0.51.0,>=0.40.0->fastapi>=0.109.0->-r /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/requirements.txt (line 1)) (1.3.1)
Requirement already satisfied: pyserial>=3.5 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from -r /home/insu/Desktop/SCANU-dev_adrian/software/layer1_radar/requirements.txt (line 5)) (3.5)
Requirement already satisfied: numpy>=1.21.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from -r /home/insu/Desktop/SCANU-dev_adrian/software/layer1_radar/requirements.txt (line 8)) (1.24.4)
Requirement already satisfied: opencv-python-headless in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (4.13.0.92)
Requirement already satisfied: numpy in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (1.24.4)
Requirement already satisfied: tqdm in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (4.67.3)
Requirement already satisfied: scikit-learn in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (1.3.2)
Requirement already satisfied: onnx in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (1.17.0)
Requirement already satisfied: ultralytics in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (8.4.47)
Requirement already satisfied: PyYAML in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (6.0.3)
Requirement already satisfied: scipy>=1.5.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from scikit-learn) (1.10.1)
Requirement already satisfied: joblib>=1.1.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from scikit-learn) (1.4.2)
Requirement already satisfied: threadpoolctl>=2.0.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from scikit-learn) (3.5.0)
Requirement already satisfied: protobuf>=3.20.2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from onnx) (5.29.6)
Requirement already satisfied: matplotlib>=3.3.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (3.7.5)
Requirement already satisfied: opencv-python>=4.6.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (4.13.0.92)
Requirement already satisfied: pillow>=7.1.2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (10.4.0)
Requirement already satisfied: requests>=2.23.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (2.32.4)
Requirement already satisfied: torch>=1.8.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (2.4.1)
Requirement already satisfied: torchvision>=0.9.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (0.19.1)
Requirement already satisfied: psutil>=5.8.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (7.2.2)
Requirement already satisfied: polars>=0.20.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (1.8.2)
Requirement already satisfied: ultralytics-thop>=2.0.18 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from ultralytics) (2.0.19)
Requirement already satisfied: contourpy>=1.0.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (1.1.1)
Requirement already satisfied: cycler>=0.10 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (0.12.1)
Requirement already satisfied: fonttools>=4.22.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (4.57.0)
Requirement already satisfied: kiwisolver>=1.0.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (1.4.7)
Requirement already satisfied: packaging>=20.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (26.2)
Requirement already satisfied: pyparsing>=2.3.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (3.1.4)
Requirement already satisfied: python-dateutil>=2.7 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (2.9.0.post0)
Requirement already satisfied: importlib-resources>=3.2.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from matplotlib>=3.3.0->ultralytics) (6.4.5)
Requirement already satisfied: charset_normalizer<4,>=2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics) (3.4.7)
Requirement already satisfied: idna<4,>=2.5 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics) (3.13)
Requirement already satisfied: urllib3<3,>=1.21.1 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics) (2.2.3)
Requirement already satisfied: certifi>=2017.4.17 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from requests>=2.23.0->ultralytics) (2026.4.22)
Requirement already satisfied: filelock in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (3.16.1)
Requirement already satisfied: typing-extensions>=4.8.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (4.13.2)
Requirement already satisfied: sympy in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (1.13.3)
Requirement already satisfied: networkx in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (3.1)
Requirement already satisfied: jinja2 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (3.1.6)
Requirement already satisfied: fsspec in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from torch>=1.8.0->ultralytics) (2025.3.0)
Requirement already satisfied: zipp>=3.1.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from importlib-resources>=3.2.0->matplotlib>=3.3.0->ultralytics) (3.20.2)
Requirement already satisfied: six>=1.5 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from python-dateutil>=2.7->matplotlib>=3.3.0->ultralytics) (1.17.0)
Requirement already satisfied: MarkupSafe>=2.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from jinja2->torch>=1.8.0->ultralytics) (2.1.5)
Requirement already satisfied: mpmath<1.4,>=1.1.0 in /home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages (from sympy->torch>=1.8.0->ultralytics) (1.3.0)
[setup] Hardware quick checks:
NVIDIA Tegra Video Input Device (platform:tegra-camrtc-ca):
	/dev/media0

NexiGo N950P 4K Webcam: NexiGo  (usb-3610000.xhci-4.1.2):
	/dev/video0
	/dev/video1
	/dev/media1

PureThermal (fw:v1.3.0): PureTh (usb-3610000.xhci-4.1.4.2):
	/dev/video2
	/dev/video3
	/dev/media2

/dev/ttyACM0
[setup] Done.
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ ./scripts/layer8.sh start
[layer8] Starting backend/UI on 0.0.0.0:8088
[layer8] Open: http://127.0.0.1:8088
[layer8] Log: /home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/backend.log
Traceback (most recent call last):
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_typing_extra.py", line 633, in _eval_type_backport
    return _eval_type(value, globalns, localns, type_params)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_typing_extra.py", line 667, in _eval_type
    return typing._eval_type(  # type: ignore
  File "/usr/lib/python3.8/typing.py", line 270, in _eval_type
    return t._evaluate(globalns, localns)
  File "/usr/lib/python3.8/typing.py", line 518, in _evaluate
    eval(self.__forward_code__, globalns, localns),
  File "<string>", line 1, in <module>
TypeError: 'type' object is not subscriptable

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/usr/lib/python3.8/runpy.py", line 194, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.8/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/__main__.py", line 4, in <module>
    uvicorn.main()
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/click/core.py", line 1161, in __call__
    return self.main(*args, **kwargs)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/click/core.py", line 1082, in main
    rv = self.invoke(ctx)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/click/core.py", line 1443, in invoke
    return ctx.invoke(self.callback, **ctx.params)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/click/core.py", line 788, in invoke
    return __callback(*args, **kwargs)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/main.py", line 412, in main
    run(
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/main.py", line 579, in run
    server.run()
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/server.py", line 65, in run
    return asyncio.run(self.serve(sockets=sockets))
  File "/usr/lib/python3.8/asyncio/runners.py", line 44, in run
    return loop.run_until_complete(main)
  File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/server.py", line 69, in serve
    await self._serve(sockets)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/server.py", line 76, in _serve
    config.load()
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/config.py", line 434, in load
    self.loaded_app = import_from_string(self.app)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/uvicorn/importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "/usr/lib/python3.8/importlib/__init__.py", line 127, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
  File "<frozen importlib._bootstrap>", line 991, in _find_and_load
  File "<frozen importlib._bootstrap>", line 975, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 671, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 848, in exec_module
  File "<frozen importlib._bootstrap>", line 219, in _call_with_frames_removed
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/app.py", line 22, in <module>
    from layer8_ui.dashboard_routes import build_router, index_handler
  File "/home/insu/Desktop/SCANU-dev_adrian/software/layer8_ui/dashboard_routes.py", line 72, in <module>
    class SettingsBody(BaseModel):
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_model_construction.py", line 219, in __new__
    set_model_fields(cls, bases, config_wrapper, ns_resolver)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_model_construction.py", line 537, in set_model_fields
    fields, class_vars = collect_model_fields(cls, bases, config_wrapper, ns_resolver, typevars_map=typevars_map)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_fields.py", line 112, in collect_model_fields
    type_hints = _typing_extra.get_model_type_hints(cls, ns_resolver=ns_resolver)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_typing_extra.py", line 509, in get_model_type_hints
    hints[name] = try_eval_type(value, globalns, localns)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_typing_extra.py", line 558, in try_eval_type
    return eval_type_backport(value, globalns, localns), True
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_typing_extra.py", line 609, in eval_type_backport
    return _eval_type_backport(value, globalns, localns, type_params)
  File "/home/insu/Desktop/SCANU-dev_adrian/software/.venv/lib/python3.8/site-packages/pydantic/_internal/_typing_extra.py", line 641, in _eval_type_backport
    raise TypeError(
TypeError: Unable to evaluate type annotation 'dict[str, Any]'. If you are making use of the new typing syntax (unions using `|` since Python 3.10 or builtins subscripting since Python 3.9), you should either replace the use of new syntax with the existing `typing` constructs or install the `eval_type_backport` package.
(.venv) insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui$ 

