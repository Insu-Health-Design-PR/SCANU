# Node 20 Recovery on Jetson (Layer 8)

Use this when `npm` is missing or `dpkg` fails with errors like:

- `trying to overwrite '/usr/include/node/common.gypi'`
- `which is also in package libnode-dev 12.x`
- `bash: npm: command not found`

## 1) Repair broken packages and remove old Node 12 stack

```bash
sudo apt --fix-broken install -y
sudo apt remove -y nodejs libnode-dev libnode72 npm || true
sudo apt autoremove -y
sudo apt clean
```

## 2) Install Node 20 cleanly from NodeSource

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 3) Verify Node and npm

```bash
node -v
npm -v
which node
which npm
```

Expected:

- `node` is `v20.x`
- `npm` exists and returns a version

## 4) Reinstall frontend dependencies

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
rm -rf node_modules package-lock.json
npm install
```

## 5) Start Layer 8 backend + frontend in one command

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_stack.sh
```

## 6) Open the UI

- Local Jetson: `http://127.0.0.1:4173`
- LAN device: `http://<JETSON_IP>:4173`

Get Jetson IP:

```bash
hostname -I
```

## If frontend still stops

Check log:

```bash
cat ~/Desktop/SCANU-dev_adrian/software/layer8_ui/logs/frontend.dev.log
```
