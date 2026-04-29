# SCAN-U Jetson Setup - Branch `dev_kpr-layer8`

Guia rapida para dejar listo un Jetson que ya tiene el codigo actualizado del repositorio:

```bash
https://github.com/Insu-Health-Design-PR/SCANU.git
```

Branch usada:

```bash
dev_kpr-layer8
```

En esta branch, el dashboard Layer 8 se sirve directamente desde el backend del Jetson en:

```text
http://<JETSON_IP>:8088/
```

No necesitas Vercel ni Cloudflare para este flujo.

---

## 0. Suposiciones

Esta guia asume que el repo ya esta en el Jetson en esta ruta:

```bash
~/Desktop/SCANU-dev_kpr-layer8
```

Si tu ruta es diferente, reemplaza esa ruta en todos los comandos.

---

## 1. Verificar branch actual

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8
git branch --show-current
```

Debe mostrar:

```text
dev_kpr-layer8
```

Si no estas en esa branch:

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8
git fetch origin
git checkout dev_kpr-layer8
git pull origin dev_kpr-layer8
```

---

## 2. Actualizar el Jetson e instalar dependencias del sistema

```bash
sudo apt update
sudo apt upgrade -y

sudo apt install -y \
  git curl wget build-essential cmake pkg-config \
  python3 python3-pip python3-venv python3-dev \
  v4l-utils ffmpeg lsof jq \
  libgl1 libglib2.0-0 libusb-1.0-0-dev
```

Dar permisos al usuario para camara, USB y radar:

```bash
sudo usermod -aG dialout,video,plugdev $USER
```

Reiniciar:

```bash
sudo reboot
```

Despues del reboot, verifica permisos y dispositivos:

```bash
groups
v4l2-ctl --list-devices
ls /dev/ttyUSB* 2>/dev/null || true
```

---

## 3. Crear o actualizar el ambiente Python

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip setuptools wheel
```

---

## 4. Instalar dependencias principales

Desde `software/`:

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software
source .venv/bin/activate

pip install -r layer8_ui/requirements.txt
pip install -r layer1_radar/requirements.txt
```

Estas dependencias cubren:

- Backend Layer 8 con FastAPI / Uvicorn.
- Radar Layer 1 con PySerial y NumPy.

---

## 5. Instalar dependencias de AI / deteccion de armas

Primero verifica si PyTorch ya esta instalado y compatible con Jetson:

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software
source .venv/bin/activate

python3 - <<'PY'
try:
    import torch
    print("torch:", torch.__version__)
    print("cuda available:", torch.cuda.is_available())
except Exception as exc:
    print("torch failed:", exc)

try:
    import torchvision
    print("torchvision:", torchvision.__version__)
except Exception as exc:
    print("torchvision failed:", exc)
PY
```

Si `torch` funciona, instala el resto de dependencias de AI:

```bash
pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
```

### Nota importante sobre PyTorch en Jetson

No es recomendable instalar PyTorch generico con:

```bash
pip install torch torchvision
```

en Jetson sin verificar compatibilidad con JetPack/NVIDIA. Si PyTorch falla, instala la version compatible con tu JetPack antes de instalar `ultralytics` o los componentes de Layer 4.

---

## 6. Verificar camaras y radar

```bash
v4l2-ctl --list-devices
ls /dev/ttyUSB* 2>/dev/null || true
```

Defaults esperados en `software/layer8_ui/ui_settings.json`:

```text
thermal_device: 1
webcam_device: 2
mmwave cli_port: /dev/ttyUSB0
mmwave data_port: /dev/ttyUSB1
backend port: 8088
```

Si los devices no coinciden, edita:

```bash
nano ~/Desktop/SCANU-dev_kpr-layer8/software/layer8_ui/ui_settings.json
```

Busca estas secciones:

```json
"thermal": {
  "thermal_device": 1
}
```

```json
"webcam": {
  "webcam_device": 2
}
```

```json
"mmwave": {
  "cli_port": "/dev/ttyUSB0",
  "data_port": "/dev/ttyUSB1"
}
```

Ajusta los valores segun lo que muestre:

```bash
v4l2-ctl --list-devices
ls /dev/ttyUSB*
```

---

## 7. Correr el dashboard Layer 8

Importante: corre el backend desde la carpeta `software/`.

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software
source .venv/bin/activate

python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Abrir en el Jetson:

```text
http://127.0.0.1:8088/
```

Desde otra computadora en la misma red:

```bash
hostname -I
```

Luego abrir:

```text
http://<JETSON_IP>:8088/
```

---

## 8. Probar API del backend

En otra terminal:

```bash
curl http://127.0.0.1:8088/api/status
curl http://127.0.0.1:8088/api/health
```

---

## 9. Controlar sensores desde terminal

Prender todos los sensores:

```bash
curl -X POST http://127.0.0.1:8088/api/run_all
```

Ver status:

```bash
curl http://127.0.0.1:8088/api/status
```

Detener todos los sensores:

```bash
curl -X POST http://127.0.0.1:8088/api/stop_all
```

Reiniciar sensores:

```bash
curl -X POST http://127.0.0.1:8088/api/restart_all
```

---

## 10. Comando rapido para correr despues de instalar todo

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8

git fetch origin
git checkout dev_kpr-layer8
git pull origin dev_kpr-layer8

cd software
source .venv/bin/activate

python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Luego abre:

```text
http://<JETSON_IP>:8088/
```

---

## 11. Crear servicio systemd opcional

Esto deja el dashboard levantando automaticamente cuando prende el Jetson.

### Crear servicio

```bash
USER_NAME="$(whoami)"
REPO="/home/$USER_NAME/Desktop/SCANU-dev_kpr-layer8"

sudo tee /etc/systemd/system/scanu-layer8.service >/dev/null <<EOF
[Unit]
Description=SCANU Layer 8 Dashboard dev_kpr-layer8
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$REPO/software
Environment=PATH=$REPO/software/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$REPO/software/.venv/bin/python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### Activar servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now scanu-layer8.service
```

### Ver estado

```bash
systemctl status scanu-layer8.service --no-pager
```

### Ver logs

```bash
journalctl -u scanu-layer8.service -f
```

### Detener servicio

```bash
sudo systemctl stop scanu-layer8.service
```

### Reiniciar servicio

```bash
sudo systemctl restart scanu-layer8.service
```

---

## 12. Troubleshooting

### Error: puerto 8088 ocupado

```bash
lsof -i :8088
```

Mata el proceso:

```bash
kill -9 <PID>
```

O corre en otro puerto:

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software
source .venv/bin/activate

python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8089
```

Abrir:

```text
http://<JETSON_IP>:8089/
```

---

### No puedo abrir desde otra computadora

Verifica IP:

```bash
hostname -I
```

Verifica que Uvicorn escucha en `0.0.0.0`:

```bash
ss -ltnp | grep 8088
```

Debe verse algo como:

```text
0.0.0.0:8088
```

Si aparece solo `127.0.0.1:8088`, vuelve a correr con:

```bash
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

---

### Camaras no aparecen

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

Prueba una camara con FFmpeg:

```bash
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg
```

Si el indice correcto no es el del archivo `ui_settings.json`, editalo:

```bash
nano ~/Desktop/SCANU-dev_kpr-layer8/software/layer8_ui/ui_settings.json
```

---

### Radar no aparece

```bash
ls /dev/ttyUSB*
dmesg | tail -n 50
```

Verifica permisos:

```bash
groups
```

Debe incluir:

```text
dialout
```

Si no aparece:

```bash
sudo usermod -aG dialout $USER
sudo reboot
```

---

### PyTorch no detecta CUDA

Dentro del venv:

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software
source .venv/bin/activate

python3 - <<'PY'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY
```

Si `cuda available` sale `False`, revisa JetPack, CUDA y version de PyTorch instalada.

---

## 13. Checklist final

```text
[ ] Jetson actualizado con apt
[ ] Usuario agregado a dialout/video/plugdev
[ ] Repo en branch dev_kpr-layer8
[ ] Ambiente Python creado en software/.venv
[ ] Dependencias Layer 8 instaladas
[ ] Dependencias Layer 1 radar instaladas
[ ] AI deps instaladas sin romper PyTorch
[ ] v4l2-ctl muestra camaras
[ ] ls /dev/ttyUSB* muestra radar
[ ] ui_settings.json tiene devices correctos
[ ] Dashboard abre en http://127.0.0.1:8088/
[ ] Dashboard abre desde otra PC en http://<JETSON_IP>:8088/
[ ] /api/status responde
[ ] /api/run_all prende sensores
```

---

## 14. Resumen minimo de comandos

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl wget build-essential cmake pkg-config python3 python3-pip python3-venv python3-dev v4l-utils ffmpeg lsof jq libgl1 libglib2.0-0 libusb-1.0-0-dev
sudo usermod -aG dialout,video,plugdev $USER
sudo reboot
```

Despues del reboot:

```bash
cd ~/Desktop/SCANU-dev_kpr-layer8/software
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel

pip install -r layer8_ui/requirements.txt
pip install -r layer1_radar/requirements.txt
pip install opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML

python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Abrir:

```text
http://<JETSON_IP>:8088/
```








444444444444444

cd ~/Desktop/SCANU-dev_adrian/software

sudo apt update
sudo apt install -y python3-venv python3-pip
sudo apt install -y python3.8-venv || true
sudo apt install -y python3.10-venv || true

rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel




cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/setup_layer8_jetson_demo.sh
