# SCANU — Arranque rápido (Jetson)

## Una sola vez (setup)

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r layer1_radar/requirements.txt
pip install -r layer8_ui/requirements.txt
pip install matplotlib opencv-python-headless numpy tqdm scikit-learn onnx ultralytics PyYAML
pip install eval_type_backport requests
sudo usermod -aG dialout,video,plugdev $USER
# Cerrar sesión y volver
```

## Cada vez (arrancar todo)

```bash
cd ~/Desktop/SCANU-dev_adrian/software
source .venv/bin/activate
python3 run.py
```

El menú arranca el backend, detecta la IP de Tailscale y te da control total:

```
══════════════════════════════════════════
         SCANU — Control Panel
══════════════════════════════════════════
 Backend:  ● ONLINE  100.92.1.128:8088

 Sensors:
   mmWave    ● RUNNING  [192 chirps, CFAR 6 dB]
   Webcam    ● RUNNING  [YOLOv8 gun detection]
   Thermal   ● RUNNING

 Threat:  CLEAR    State: IDLE

 [1] Start all     [2] Stop all      [3] Restart all
 [4] mmWave ↕      [5] Webcam ↕      [6] Thermal ↕
 [R] Record 30s    [D] JSON dump     [M] Live metrics
 [L] View logs     [0] Exit
══════════════════════════════════════════
```

## Frontend (laptop)

```bash
cd ~/Desktop/SCANU-UI
echo 'VITE_LAYER8_API_BASE=http://100.92.1.128:8088' > .env.local
npm run dev
```

Abre `http://localhost:5173`. El frontend se conecta al Jetson vía Tailscale.
