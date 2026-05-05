# SCANU — Guía de instalación completa (Jetson + Frontend)

Esta guía cubre la instalación de dependencias para ejecutar SCANU en dos entornos:
- **Jetson** (NVIDIA Orin/AGX): backend Python + sensores (mmWave, térmica, webcam)
- **Laptop / Vercel**: frontend React (SCANU-UI) que se comunica con el Jetson vía Tailscale

---

## 1. Jetson — Backend (Python 3.10+)

### 1.1 Paquetes del sistema

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  git curl wget build-essential cmake pkg-config \
  python3 python3-pip python3-venv python3-dev \
  v4l-utils ffmpeg lsof jq \
  libgl1 libglib2.0-0 libusb-1.0.0-dev \
  libjpeg-dev zlib1g-dev libopenblas-dev
```

### 1.2 Permisos para sensores

```bash
sudo usermod -aG dialout,video,plugdev $USER
# Cierra sesión y vuelve a entrar para que aplique
```

### 1.3 Clonar el repositorio

```bash
cd ~/Desktop
git clone https://github.com/Insu-Health-Design-PR/SCANU.git
cd SCANU
git checkout dev_adrian
```

### 1.4 Entorno virtual Python

```bash
cd ~/Desktop/SCANU
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### 1.5 Dependencias Python por capa

```bash
# Capa 1 — Radar + sensores
pip install -r software/layer1_radar/requirements.txt

# Capa 4 — Inferencia AI (PyTorch, YOLOv8, OpenCV)
# En Jetson: usar wheels oficiales de NVIDIA para PyTorch
# Ver https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
# Ejemplo para JetPack 6 / L4T R36:
# wget https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/...
pip install -r software/layer4_inference/requirements.txt

# Capa 8 — Dashboard backend (FastAPI)
pip install -r software/layer8_ui/requirements.txt
```

### 1.6 Infineon Radar SDK (sensor de presencia LTR11)

```bash
# Solicitar acceso en: https://www.infineon.com/cms/en/product/sensor/radar-sensors/
# Descargar ifxradarsdk y colocarlo en:
#   ~/Desktop/SCANU/software/vendor/ifx_radar_sdk/
# Instalar:
cd ~/Desktop/SCANU/software/vendor/ifx_radar_sdk
pip install .
```

> **Nota:** El sistema funciona sin el Infineon LTR11 (solo presencia). El mmWave IWR6843 y la cámara térmica son los sensores principales.

### 1.7 Tailscale (conexión remota)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Anota la IP de Tailscale del Jetson (ej: 100.92.1.128)
```

### 1.8 Verificar instalación

```bash
cd ~/Desktop/SCANU
source .venv/bin/activate
PYTHONPATH="$PWD:$PWD/software" python3 -c "
from layer5_fusion import L1L2FusionAdapter
from layer6_state_machine.orchestrator import Layer6Orchestrator
from layer6_state_machine.models import WeaponStateMachineConfig
print('✓ Backend imports OK')
"
```

---

## 2. Laptop — Frontend (Node.js 20+)

### 2.1 Node.js

```bash
# macOS
brew install node@20

# Linux
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2.2 Clonar el frontend

```bash
cd ~/Desktop
git clone https://github.com/Insu-Health-Design-PR/SCANU-UI.git
cd SCANU-UI
```

### 2.3 Instalar dependencias

```bash
npm ci
```

### 2.4 Configurar conexión al Jetson

Crear `.env.local`:

```bash
# Si el Jetson está en Tailscale con IP 100.92.1.128:
VITE_LAYER8_API_BASE=http://100.92.1.128:8088
VITE_LAYER8_API_KEY=
```

### 2.5 Tailscale en la laptop

```bash
# macOS
brew install tailscale
sudo tailscale up

# Linux
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### 2.6 Verificar

```bash
npm run dev
# Abre http://localhost:5173
# El proxy de Vite redirige /api al Jetson
```

---

## 3. Configurar el modo weapon-optimised

Editar `software/layer8_ui/ui_settings.json` en el Jetson:

```json
{
  "mmwave": {
    "frames": 0,
    "wpn": true,
    "mmwave_only": 1,
    "cli_port": "/dev/ttyUSB0",
    "data_port": "/dev/ttyUSB1",
    "output": "layer8_ui/artifacts/mmwave_frames.json",
    "live_frame": "layer8_ui/artifacts/live_mmwave.jpg",
    "no_frame_timeout_s": 30,
    "verbose": false,
    "extra_args": "--auto-recover-restart"
  }
}
```

| Campo | Valor | Significado |
|-------|-------|-------------|
| `frames` | `0` | Modo continuo (no se apaga solo) |
| `wpn` | `true` | Activa 192 chirps, CFAR 6 dB, clutter removal, heatmaps |
| `cli_port` | `/dev/ttyUSB0` | Puerto de comandos del IWR6843 |
| `data_port` | `/dev/ttyUSB1` | Puerto de datos TLV |
| `output` | `layer8_ui/artifacts/mmwave_frames.json` | Salida JSON para el dashboard |

---

## 4. Arrancar el sistema

### 4.1 En el Jetson

```bash
cd ~/Desktop/SCANU
source .venv/bin/activate
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

El dashboard quedará en `http://<JETSON_IP>:8088/` (HTML estático incluido en el backend).

### 4.2 En la laptop (opcional — frontend separado)

```bash
cd ~/Desktop/SCANU-UI
npm run dev
# Abre http://localhost:5173
```

### 4.3 En Vercel (producción)

```bash
cd ~/Desktop/SCANU-UI
npm run build
# El directorio dist/ se despliega en Vercel
# Variables de entorno en Vercel:
#   VITE_LAYER8_API_BASE=https://<túnel-cloudflare>
#   VITE_LAYER8_API_KEY=<api-key>
```

---

## 5. Verificación rápida

```bash
# En el Jetson — chequear que el backend responde
curl http://localhost:8088/api/health

# En el Jetson — iniciar todos los sensores desde el dashboard
curl -X POST http://localhost:8088/api/run_all

# En la laptop — verificar conectividad
curl http://100.92.1.128:8088/api/health

# En la laptop — validar todos los endpoints
cd ~/Desktop/SCANU-UI
npm run test:endpoints
```

---

## 6. Dependencias resumidas

### Jetson (backend)

| Paquete | Uso |
|---------|-----|
| `pyserial` | Comunicación UART con IWR6843 |
| `numpy` | Procesamiento de señales |
| `opencv-python-headless` | Captura V4L2 (cámaras) |
| `torch`, `torchvision` | Inferencia YOLOv8 (GPU Jetson) |
| `ultralytics` | YOLOv8 para detección de armas |
| `fastapi`, `uvicorn` | Servidor HTTP/WebSocket |
| `matplotlib` | Visualización en live_capture.py |
| `scikit-learn` | Utilidades ML |
| `onnx` | Exportación de modelos |
| `ifxradarsdk` | Sensor Infineon LTR11 (opcional) |

### Laptop (frontend)

| Paquete | Uso |
|---------|-----|
| `react`, `react-dom` | UI framework |
| `zustand` | Estado global |
| `framer-motion` | Animaciones |
| `lucide-react` | Iconos |
| `tailwindcss` | Estilos |
| `vite` | Build tool + dev server |
| `typescript` | Tipado estático |

---

## 7. Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: software` | PYTHONPATH no incluye el repo: `export PYTHONPATH=~/Desktop/SCANU:~/Desktop/SCANU/software` |
| Radar no detecta puertos | `ls /dev/ttyUSB*` y `ls /dev/ttyACM*`. Probar `sudo chmod 666 /dev/ttyUSB*` |
| Cámara no abre | `v4l2-ctl --list-devices`. Verificar índice en settings. |
| PyTorch no usa GPU | Instalar wheel NVIDIA específico para la versión de JetPack |
| Frontend no conecta | Verificar Tailscale: `tailscale status`. Ambos dispositivos deben aparecer. |
| Vite proxy no funciona | Asegurar que `VITE_LAYER8_API_BASE` en `.env.local` apunta a `http://localhost:5173` (el proxy de Vite) |
