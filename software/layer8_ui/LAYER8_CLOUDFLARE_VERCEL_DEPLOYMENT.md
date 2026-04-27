# Layer 8 Cloudflare Tunnel + Vercel Deployment

Use this when the Jetson runs the backend and Vercel hosts the frontend.

Current Vercel frontend:

```text
https://scanu-ui.vercel.app
```

## 1) Start backend on Jetson

Recommended Vercel-ready command:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh
```

Backend default:

```text
http://127.0.0.1:8088
```

The Vercel-ready script sets:

```text
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8088
LAYER8_CORS_ORIGINS=https://scanu-ui.vercel.app
```

You can override CORS if needed:

```bash
LAYER8_API_KEY="change-this-key" \
LAYER8_CORS_ORIGINS="https://scanu-ui.vercel.app,https://another-preview.vercel.app" \
./scripts/start_layer8_backend_for_vercel.sh
```

## 2) Validate backend locally

Health is public:

```bash
curl -sS http://127.0.0.1:8088/api/health
```

Protected endpoints require the API key:

```bash
curl -sS -H "X-Layer8-Api-Key: change-this-key" http://127.0.0.1:8088/api/status
curl -sS -H "X-Layer8-Api-Key: change-this-key" http://127.0.0.1:8088/api/visual/latest
```

Or use the script:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
LAYER8_API_KEY="change-this-key" ./scripts/check_layer8_backend.sh
```

## 3) Start Cloudflare Tunnel

Recommended helper:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui
./scripts/start_layer8_cloudflare_tunnel.sh
```

Manual equivalent:

```bash
cloudflared tunnel --url http://127.0.0.1:8088
```

Cloudflare prints a public HTTPS URL like:

```text
https://example.trycloudflare.com
```

## 4) Validate public backend URL

```bash
BACKEND_URL="https://example.trycloudflare.com" \
LAYER8_API_KEY="change-this-key" \
./scripts/check_layer8_backend.sh
```

Manual checks:

```bash
curl -sS https://example.trycloudflare.com/api/health
curl -sS -H "X-Layer8-Api-Key: change-this-key" https://example.trycloudflare.com/api/status
curl -sS -H "X-Layer8-Api-Key: change-this-key" https://example.trycloudflare.com/api/visual/latest
```

## 5) Configure Vercel frontend environment

Set these in Vercel Project Settings -> Environment Variables:

```text
VITE_LAYER8_API_BASE=https://example.trycloudflare.com
VITE_LAYER8_WS_URL=wss://example.trycloudflare.com/ws/events
VITE_LAYER8_API_KEY=change-this-key
```

Then redeploy the Vercel project.

For the current frontend, open:

```text
https://scanu-ui.vercel.app
```

## 6) Expected frontend behavior

The Vercel frontend should load:

- RGB Camera
- Thermal Camera
- Point Cloud
- Presence Sensor
- System Status
- Console Log
- Execution Controls

The browser console should not show CORS, mixed-content, or WebSocket connection errors.

## 7) End-to-end order

Use this order when testing with the Jetson:

```bash
cd ~/Desktop/SCANU-dev_adrian/software/layer8_ui

# Terminal 1: backend
LAYER8_API_KEY="change-this-key" ./scripts/start_layer8_backend_for_vercel.sh

# Terminal 2: tunnel
./scripts/start_layer8_cloudflare_tunnel.sh

# Terminal 3: public checks after copying the tunnel URL
BACKEND_URL="https://example.trycloudflare.com" \
LAYER8_API_KEY="change-this-key" \
./scripts/check_layer8_backend.sh
```

Then update Vercel with the same tunnel URL and API key, redeploy, and open:

```text
https://scanu-ui.vercel.app
```

## Security note

This API key is demo-level protection. Browser environment variables are visible to users after build, so do not treat this as production-grade authentication.
