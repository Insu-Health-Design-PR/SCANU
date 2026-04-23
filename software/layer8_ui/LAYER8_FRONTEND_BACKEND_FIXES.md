# Layer 8 Frontend/Backend Fixes (Jetson)

Base path on Jetson:

```bash
~/Desktop/SCANU-dev_adrian/software/layer8_ui
```

## 1) `npm: command not found`

If Node/npm is broken or missing:

```bash
sudo apt --fix-broken install -y
sudo apt remove -y nodejs libnode-dev libnode72 npm || true
sudo apt autoremove -y
sudo apt clean
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

Then reinstall frontend dependencies:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
rm -rf node_modules package-lock.json
npm install
npx vite --version
```

## 2) `vite: not found`

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
npm install
npx vite --version
```

If it still fails, clean and reinstall:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
rm -rf node_modules package-lock.json
npm install
```

## 3) CORS errors in browser console

Make sure backend and frontend are both running from:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

Default backend is now `8087`.  
If you force another port, set both env vars too:

```bash
BACKEND_PORT=8087 \
VITE_LAYER8_API_BASE="http://127.0.0.1:8087" \
VITE_LAYER8_WS_URL="ws://127.0.0.1:8087/ws/events" \
./scripts/start_layer8_stack.sh
```

## 4) Frontend opens but no live data

Run live verification:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/verify_layer8_live_jetson.sh
```

Check backend endpoints:

```bash
curl -s http://127.0.0.1:8087/api/status | jq
curl -s http://127.0.0.1:8087/api/health | jq
curl -s http://127.0.0.1:8087/api/layers/summary | jq
```

## 5) Check logs quickly

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
tail -n 120 logs/backend.dev.log
tail -n 120 logs/frontend.dev.log
```

## 6) Port already in use

```bash
lsof -i :4173
lsof -i :8087
```

Then stop old process and run again:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

