# Layer 8 Jetson E2E (60s)

This guide is for your Jetson path:

```bash
~/Desktop/SCANU-dev_adrian/software
```

## 0) Install dependencies first (recommended)

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m pip install -r layer8_ui/requirements.txt
cd layer8_ui/frontend
npm install
```

## 1) Start backend + frontend together (single command)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
chmod +x scripts/start_layer8_stack.sh
./scripts/start_layer8_stack.sh
```

Optional first run with dependency install:

```bash
INSTALL_FRONTEND_DEPS=1 ./scripts/start_layer8_stack.sh
```

## 2) Start Layer 8 backend (Terminal A)

```bash
cd ~/Desktop/SCANU-dev_adrian/software
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8080
```

## 3) Start Layer 8 frontend (Terminal B)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
VITE_LAYER8_API_BASE="http://127.0.0.1:8080" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:8080/ws/events" \
npm run dev -- --host 0.0.0.0 --port 4173 --strictPort
```

## 4) Run 60-second verification (Terminal C)

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
chmod +x scripts/verify_layer8_e2e_60s.sh
./scripts/verify_layer8_e2e_60s.sh
```

Expected final line:

```text
[PASS] Layer 8 end-to-end compatibility checks passed
```

## 5) Open UI

Local Jetson browser:

```text
http://127.0.0.1:4173
```

From another device on LAN:

```bash
hostname -I
```

Then open:

```text
http://<JETSON_IP>:4173
```

## Notes

- This verifies frontend/backend contract endpoints used by `dashboardApi.ts`.
- If `/ws/events` check is skipped, install websockets:

```bash
pip install websockets
```

## Troubleshooting: frontend stops on Jetson

If you see `Frontend stopped` and `EBADENGINE` warnings with `node v12`, update Node first.

### 1) Check frontend log

```bash
cat ~/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/frontend.dev.log
```

### 2) Install Node 20 (recommended for Vite 5)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
```

### 3) Reinstall frontend dependencies cleanly

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
rm -rf node_modules package-lock.json
npm install
```

### 4) Start stack again

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```









