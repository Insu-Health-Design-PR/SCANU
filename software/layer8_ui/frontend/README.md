# Layer 8 React Frontend

React/Vite operator UI for SCANU Layer 8.

## Development

Run the FastAPI backend first:

```bash
cd software
python3 -m uvicorn layer8_ui.app:app --host 0.0.0.0 --port 8088
```

Then run Vite:

```bash
cd software/layer8_ui/frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` and `/ws` to the FastAPI backend.

## Production Build

```bash
npm run build
```

FastAPI serves `frontend/dist/index.html` automatically when it exists. If the
React build is missing, `/` returns a setup error telling the operator to build
the frontend.
