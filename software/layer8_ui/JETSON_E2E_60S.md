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









7777777777777777








insu@insu-desktop:~$ cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend
rm -rf node_modules package-lock.json
npm install
bash: npm: command not found
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend$ npm install
bash: npm: command not found
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend$ npm install
bash: npm: command not found
insu@insu-desktop:~/Desktop/SCANU-dev_adrian/software/layer8_ui/frontend$ curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
[sudo] password for insu: 
2026-04-22 10:59:35 - Installing pre-requisites
Get:1 file:/var/cudnn-local-tegra-repo-ubuntu2204-9.3.0  InRelease [1,572 B]
Get:1 file:/var/cudnn-local-tegra-repo-ubuntu2204-9.3.0  InRelease [1,572 B]
Get:2 file:/var/l4t-cuda-tegra-repo-ubuntu2204-12-6-local  InRelease [1,572 B] 
Get:3 file:/var/nv-tensorrt-local-tegra-repo-ubuntu2204-10.3.0-cuda-12.5  InRelease [1,572 B]
Get:2 file:/var/l4t-cuda-tegra-repo-ubuntu2204-12-6-local  InRelease [1,572 B] 
Get:3 file:/var/nv-tensorrt-local-tegra-repo-ubuntu2204-10.3.0-cuda-12.5  InRelease [1,572 B]
Hit:4 https://deb.nodesource.com/node_20.x nodistro InRelease                  
Hit:5 https://download.docker.com/linux/ubuntu jammy InRelease                 
Get:6 https://pkgs.tailscale.com/stable/ubuntu jammy InRelease                 
Hit:7 https://repo.download.nvidia.com/jetson/common r36.4 InRelease           
Hit:8 https://repo.download.nvidia.com/jetson/t234 r36.4 InRelease             
Hit:9 http://ports.ubuntu.com/ubuntu-ports jammy InRelease                     
Get:10 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [128 kB]   
Hit:11 https://repo.download.nvidia.com/jetson/ffmpeg r36.4 InRelease
Hit:12 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease
Hit:13 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease
Get:14 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 Packages [3,281 kB]
Get:15 http://ports.ubuntu.com/ubuntu-ports jammy-updates/universe arm64 Packages [1,314 kB]
Fetched 4,729 kB in 14s (339 kB/s)                                             
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
39 packages can be upgraded. Run 'apt list --upgradable' to see them.
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
ca-certificates is already the newest version (20240203~22.04.1).
curl is already the newest version (7.81.0-1ubuntu1.23).
gnupg is already the newest version (2.2.27-3ubuntu2.5).
apt-transport-https is already the newest version (2.4.14).
The following packages were automatically installed and are no longer required:
  gyp libavcodec58 libavfilter7 libavformat58 libavutil56 libjs-events
  libjs-highlight.js libjs-inherits libjs-is-typedarray libjs-psl
  libjs-source-map libjs-sprintf-js libjs-typedarray-to-buffer libnode-dev
  libnode72 libpostproc55 libssh-gcrypt-4 libssl-dev libswresample3
  libswscale5 libuv1-dev libva-x11-2 libvdpau1 node-abab node-abbrev
  node-agent-base node-ansi-regex node-ansi-styles node-ansistyles node-aproba
  node-archy node-are-we-there-yet node-argparse node-arrify node-asap
  node-asynckit node-balanced-match node-brace-expansion node-builtins
  node-chalk node-chownr node-clean-yaml-object node-cli-table node-clone
  node-color-convert node-color-name node-colors node-columnify
  node-combined-stream node-commander node-console-control-strings
  node-core-util-is node-cssom node-cssstyle node-debug
  node-decompress-response node-defaults node-delayed-stream node-delegates
  node-depd node-diff node-encoding node-end-of-stream node-err-code
  node-escape-string-regexp node-events node-fancy-log node-foreground-child
  node-fs-write-stream-atomic node-fs.realpath node-function-bind node-gauge
  node-get-stream node-glob node-got node-graceful-fs node-growl node-has-flag
  node-has-unicode node-hosted-git-info node-https-proxy-agent node-iconv-lite
  node-iferr node-imurmurhash node-indent-string node-inflight node-inherits
  node-ini node-ip node-ip-regex node-is-buffer node-is-plain-obj
  node-is-typedarray node-isarray node-isexe node-json-buffer
  node-json-parse-better-errors node-jsonparse node-kind-of node-lcov-parse
  node-lodash-packages node-log-driver node-lowercase-keys node-lru-cache
  node-mimic-response node-minimatch node-minimist node-minipass node-ms
  node-mute-stream node-negotiator node-normalize-package-data
  node-npm-bundled node-npm-package-arg node-npmlog node-object-assign
  node-once node-osenv node-p-cancelable node-p-map node-path-is-absolute
  node-process-nextick-args node-promise-inflight node-promise-retry
  node-promzard node-psl node-pump node-punycode node-quick-lru node-read
  node-read-package-json node-readable-stream node-resolve node-retry
  node-rimraf node-run-queue node-safe-buffer node-semver node-set-blocking
  node-signal-exit node-slash node-slice-ansi node-source-map
  node-source-map-support node-spdx-correct node-spdx-exceptions
  node-spdx-expression-parse node-spdx-license-ids node-sprintf-js node-ssri
  node-stack-utils node-stealthy-require node-string-decoder node-string-width
  node-strip-ansi node-supports-color node-text-table node-time-stamp
  node-tmatch node-tough-cookie node-typedarray-to-buffer node-unique-filename
  node-universalify node-util-deprecate node-validate-npm-package-license
  node-validate-npm-package-name node-wcwidth.js node-webidl-conversions
  node-whatwg-fetch node-wide-align node-wrappy node-write-file-atomic
  node-yallist nodejs
Use 'sudo apt autoremove' to remove them.
0 upgraded, 0 newly installed, 0 to remove and 39 not upgraded.
gpg: WARNING: unsafe ownership on homedir '/home/insu/.gnupg'
Get:1 file:/var/cudnn-local-tegra-repo-ubuntu2204-9.3.0  InRelease [1,572 B]
Get:2 file:/var/l4t-cuda-tegra-repo-ubuntu2204-12-6-local  InRelease [1,572 B]
Get:1 file:/var/cudnn-local-tegra-repo-ubuntu2204-9.3.0  InRelease [1,572 B]   
Get:3 file:/var/nv-tensorrt-local-tegra-repo-ubuntu2204-10.3.0-cuda-12.5  InRelease [1,572 B]
Get:2 file:/var/l4t-cuda-tegra-repo-ubuntu2204-12-6-local  InRelease [1,572 B] 
Get:3 file:/var/nv-tensorrt-local-tegra-repo-ubuntu2204-10.3.0-cuda-12.5  InRelease [1,572 B]
Hit:4 https://download.docker.com/linux/ubuntu jammy InRelease                 
Get:5 https://pkgs.tailscale.com/stable/ubuntu jammy InRelease                 
Hit:6 https://deb.nodesource.com/node_20.x nodistro InRelease                  
Hit:7 https://repo.download.nvidia.com/jetson/common r36.4 InRelease           
Hit:8 http://ports.ubuntu.com/ubuntu-ports jammy InRelease                     
Hit:9 https://repo.download.nvidia.com/jetson/t234 r36.4 InRelease
Hit:10 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease            
Hit:11 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease          
Hit:12 https://repo.download.nvidia.com/jetson/ffmpeg r36.4 InRelease
Hit:13 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease
Fetched 6,581 B in 3s (2,563 B/s)
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
39 packages can be upgraded. Run 'apt list --upgradable' to see them.
2026-04-22 11:00:07 - Repository configured successfully.
2026-04-22 11:00:07 - To install Node.js, run: apt install nodejs -y
2026-04-22 11:00:07 - You can use N|solid Runtime as a node.js alternative
2026-04-22 11:00:07 - To install N|solid Runtime, run: apt install nsolid -y 

Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
The following packages were automatically installed and are no longer required:
  gyp libavcodec58 libavfilter7 libavformat58 libavutil56 libjs-events
  libjs-highlight.js libjs-inherits libjs-is-typedarray libjs-psl
  libjs-source-map libjs-sprintf-js libjs-typedarray-to-buffer libnode-dev
  libnode72 libpostproc55 libssh-gcrypt-4 libssl-dev libswresample3
  libswscale5 libuv1-dev libva-x11-2 libvdpau1 node-abab node-abbrev
  node-agent-base node-ansi-regex node-ansi-styles node-ansistyles node-aproba
  node-archy node-are-we-there-yet node-argparse node-arrify node-asap
  node-asynckit node-balanced-match node-brace-expansion node-builtins
  node-chalk node-chownr node-clean-yaml-object node-cli-table node-clone
  node-color-convert node-color-name node-colors node-columnify
  node-combined-stream node-commander node-console-control-strings
  node-core-util-is node-cssom node-cssstyle node-debug
  node-decompress-response node-defaults node-delayed-stream node-delegates
  node-depd node-diff node-encoding node-end-of-stream node-err-code
  node-escape-string-regexp node-events node-fancy-log node-foreground-child
  node-fs-write-stream-atomic node-fs.realpath node-function-bind node-gauge
  node-get-stream node-glob node-got node-graceful-fs node-growl node-has-flag
  node-has-unicode node-hosted-git-info node-https-proxy-agent node-iconv-lite
  node-iferr node-imurmurhash node-indent-string node-inflight node-inherits
  node-ini node-ip node-ip-regex node-is-buffer node-is-plain-obj
  node-is-typedarray node-isarray node-isexe node-json-buffer
  node-json-parse-better-errors node-jsonparse node-kind-of node-lcov-parse
  node-lodash-packages node-log-driver node-lowercase-keys node-lru-cache
  node-mimic-response node-minimatch node-minimist node-minipass node-ms
  node-mute-stream node-negotiator node-normalize-package-data
  node-npm-bundled node-npm-package-arg node-npmlog node-object-assign
  node-once node-osenv node-p-cancelable node-p-map node-path-is-absolute
  node-process-nextick-args node-promise-inflight node-promise-retry
  node-promzard node-psl node-pump node-punycode node-quick-lru node-read
  node-read-package-json node-readable-stream node-resolve node-retry
  node-rimraf node-run-queue node-safe-buffer node-semver node-set-blocking
  node-signal-exit node-slash node-slice-ansi node-source-map
  node-source-map-support node-spdx-correct node-spdx-exceptions
  node-spdx-expression-parse node-spdx-license-ids node-sprintf-js node-ssri
  node-stack-utils node-stealthy-require node-string-decoder node-string-width
  node-strip-ansi node-supports-color node-text-table node-time-stamp
  node-tmatch node-tough-cookie node-typedarray-to-buffer node-unique-filename
  node-universalify node-util-deprecate node-validate-npm-package-license
  node-validate-npm-package-name node-wcwidth.js node-webidl-conversions
  node-whatwg-fetch node-wide-align node-wrappy node-write-file-atomic
  node-yallist
Use 'sudo apt autoremove' to remove them.
The following packages will be upgraded:
  nodejs
1 upgraded, 0 newly installed, 0 to remove and 38 not upgraded.
Need to get 0 B/31.3 MB of archives.
After this operation, 195 MB of additional disk space will be used.
debconf: delaying package configuration, since apt-utils is not installed
(Reading database ... 214560 files and directories currently installed.)
Preparing to unpack .../nodejs_20.20.2-1nodesource1_arm64.deb ...
Unpacking nodejs (20.20.2-1nodesource1) over (12.22.9~dfsg-1ubuntu3.6) ...
dpkg: error processing archive /var/cache/apt/archives/nodejs_20.20.2-1nodesource1_arm64.deb (--unpack):
 trying to overwrite '/usr/include/node/common.gypi', which is also in package libnode-dev 12.22.9~dfsg-1ubuntu3.6
dpkg-deb: error: paste subprocess was killed by signal (Broken pipe)
Errors were encountered while processing:
 /var/cache/apt/archives/nodejs_20.20.2-1nodesource1_arm64.deb
E: Sub-process /usr/bin/dpkg returned an error code (1)
v12.22.9
bash: npm: command not found

