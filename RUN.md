# SCANU — Cómo correr en el Jetson

## Setup Inicial

```bash
cd ~/Desktop/SCANU/software/layer8_ui
INSTALL_SYSTEM_DEPS=1 ./scripts/layer8.sh setup
```

El entorno virtual canónico queda en:

```text
~/Desktop/SCANU/software/.venv
```

## Arrancar

```bash
cd ~/Desktop/SCANU/software/layer8_ui
./scripts/layer8.sh start
```

Abre:

```text
http://<IP-DEL-JETSON>:8088
```

## Iniciar Sensores

En el dashboard, botón **Run All**.

O por API:

```bash
curl -X POST http://localhost:8088/api/run_all
```

## Verificar

```bash
curl http://localhost:8088/api/status | python3 -m json.tool
curl http://localhost:8088/api/status/mmwave
curl http://localhost:8088/api/dashboard/metrics
```

## Parar Todo

```bash
curl -X POST http://localhost:8088/api/stop_all
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: layer8_ui` | Activa `source ~/Desktop/SCANU/software/.venv/bin/activate` y arranca desde `~/Desktop/SCANU/software/layer8_ui`. |
| Radar sin datos | `ls /dev/ttyUSB*`, verifica puertos en `ui_settings.json`. |
| Cámara no abre | `v4l2-ctl --list-devices`, ajusta índice en settings. |
| Dashboard no carga | Revisa `software/layer8_ui/logs/backend.dev.log` y el puerto `8088`. |
| Tailscale no conecta | `tailscale status`, ambos dispositivos deben aparecer. |
