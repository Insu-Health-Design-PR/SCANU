# SCANU — Cómo correr en el Jetson

## Setup inicial (solo la primera vez)

```bash
cd ~/Desktop/SCANU

# 1. Paquetes del sistema
sudo apt install -y python3-venv python3-dev v4l-utils ffmpeg lsof \
  libgl1 libglib2.0-0 libusb-1.0-0-dev libjpeg-dev

# 2. Permisos para sensores
sudo usermod -aG dialout,video,plugdev $USER
# Cierra sesión y vuelve a entrar

# 3. Venv exclusivo para esta branch
python3 -m venv .venv-adrian
source .venv-adrian/bin/activate
pip install --upgrade pip setuptools wheel

# 4. Dependencias Python
pip install -r software/layer1_radar/requirements.txt
pip install -r software/layer8_ui/requirements.txt
pip install matplotlib

# 5. PyTorch para Jetson (wheel NVIDIA)
# Verifica JetPack: cat /etc/nv_tegra_release
# JetPack 6 → descarga el wheel correspondiente de:
# https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
pip install torch-2.1.0-cp310-cp310-linux_aarch64.whl
pip install torchvision ultralytics opencv-python-headless scikit-learn onnx PyYAML tqdm

# 6. PYTHONPATH automático al activar el venv
echo 'export PYTHONPATH="$HOME/Desktop/SCANU:$HOME/Desktop/SCANU/software"' >> .venv-adrian/bin/activate
```

## Arrancar (cada vez)

```bash
cd ~/Desktop/SCANU
source .venv-adrian/bin/activate
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Abre en el navegador: `http://<IP-DEL-JETSON>:8088`

## Iniciar los sensores

En el dashboard, botón **Run All** (arranca mmWave, térmica y webcam simultáneamente).

O por API:

```bash
curl -X POST http://localhost:8088/api/run_all
```

## Verificar que funciona

```bash
# Estado de los sensores
curl http://localhost:8088/api/status | python3 -m json.tool

# ¿El mmWave está corriendo en modo armas?
curl http://localhost:8088/api/status/mmwave

# ¿Hay detección?
curl http://localhost:8088/api/dashboard/metrics
```

## Parar todo

```bash
curl -X POST http://localhost:8088/api/stop_all
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: software` | Activa el venv: `source .venv-adrian/bin/activate` |
| Radar sin datos | `ls /dev/ttyUSB*`, verifica puertos en `ui_settings.json` |
| Cámara no abre | `v4l2-ctl --list-devices`, ajusta índice en settings |
| Dashboard no carga | ¿Puerto 8088 abierto? `sudo ufw allow 8088` |
| Tailscale no conecta | `tailscale status`, ambos dispositivos deben aparecer |
