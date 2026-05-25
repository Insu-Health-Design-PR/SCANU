# AGENTS.md — Contexto para asistentes AI

## Proyecto: SCAN-U — Sistema de detección de objetos ocultos con radar mmWave

### Estructura del proyecto

```
software/
├── layer1_radar/           ← Drivers de radar (mmWave SDK, Infineon)
│   └── mmwave/             ← Constantes del radar TI
├── layer1_sensor_hub/      ← Hub de sensores (radar, cámara térmica)
│   ├── mmwave_dca/         ← ★ Módulo DCA1000 (captura raw ADC)
│   │   ├── dca1000_control.py     ← Control UDP del DCA1000
│   │   ├── dca1000_udp.py         ← Receptor UDP de datos ADC
│   │   ├── capture_runner.py      ← Orquestador de captura
│   │   ├── run_dca_capture.py     ← CLI entrypoint
│   │   ├── run_jetson_native_capture.sh ← Script shell
│   │   ├── adc_reader.py          ← Lectura y procesamiento ADC
│   │   ├── process_adc_file.py    ← CLI para Range-Doppler PNG
│   │   ├── diagnose_dca1000.py    ← Diagnóstico de conectividad
│   │   ├── radar_cli.py           ← Configuración radar por UART
│   │   ├── multi_sensor.py        ← Captura multi-sensor
│   │   ├── ti_cli/configFile.json ← Config JSON del DCA1000
│   │   ├── GUIA_CAPTURA_DCA1000.md  ← ★ Guía de captura (creada)
│   │   └── PRUEBAS_CAPTURA.md     ← ★ Resultados de pruebas (creada)
│   └── testing/configs/    ← Archivos .cfg del radar
│       ├── weapon_detection_dca1000.cfg  ← ★ Default para DCA1000
│       ├── dca1000_adc_capture.cfg       ← Config básica ADC
│       └── ...otros .cfg...
├── layer3_features/        ← Procesamiento de características
├── layer6_state_machine/   ← Máquina de estados
└── layer7_alerts/          ← Sistema de alertas
```

### ★ Cambios realizados en dca1000_control.py

Se corrigieron 3 problemas que impedían la comunicación con el DCA1000:

1. **Puerto origen** (línea 201):
   - ANTES: `sock.bind((self.network.pc_ip, 0))` — puerto efímero
   - DESPUÉS: `sock.bind((self.network.pc_ip, self.network.config_port))` — puerto 4096
   - El DCA1000 solo responde cuando el puerto UDP origen es 4096.

2. **connect_first** (línea 240):
   - ANTES: `connect_first: bool = True`
   - DESPUÉS: `connect_first: bool = False`
   - Este firmware del DCA1000 no implementa SYSTEM_CONNECT (0x09).
   - La secuencia correcta es: reset_fpga → fpga → packet (sin connect).

3. **Validación de respuesta** (línea 278, `_response_ok`):
   - ANTES: Revisaba que los últimos 2 bytes del "status_region" fueran cero.
   - DESPUÉS: Verifica que el footer del paquete sea 0xEEAA.
   - La respuesta de READ_FPGA_VERSION tiene datos en el payload que no son cero
     y eran interpretados falsamente como error.

### Cómo correr captura DCA1000

Siempre usar PYTHONPATH:

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software
export PYTHONPATH=/home/insu/Desktop/SCANU-dev_adrian/software:$PYTHONPATH
```

**Diagnóstico:**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.diagnose_dca1000
```

**Captura rápida:**
```bash
CLI_PORT=/dev/ttyUSB0 DURATION_S=5 \
./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

**Captura manual:**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port /dev/ttyUSB0 \
  --config layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg \
  --dca-config layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
  --output captures/adc_data.bin --duration-s 5 \
  --configure-dca --start-dca --stop-dca
```

**Procesar datos:**
```bash
python3 -m layer1_sensor_hub.mmwave_dca.process_adc_file \
  --input captures/adc_data.bin \
  --frames 100 --chirps 16 --rx 4 --samples 384 \
  --allow-truncate --output captures/range_doppler.png
```

### Protocolo DCA1000

- **Comandos** (UDP puerto 4096): `0xA55A | cmd(2B LE) | len(2B LE) | payload | 0xEEAA`
- **Datos** (UDP puerto 4098): `[10B header] [ADC data ~1456B]`
- **Formato ADC**: TI interleaved — `I0,I1,I2,I3,Q0,Q1,Q2,Q3` por sample (4 RX)
- **Tasa**: ~2000 pkt/s, ~2.79 MB/s, 1456 bytes/payload fijo

### Hardware

| Dispositivo | Conexión | IP/Puerto |
|---|---|---|
| Jetson | — | 192.168.33.30 |
| DCA1000 | Ethernet eth0 | 192.168.33.180:4096/4098 |
| Radar IWR6843 | USB (/dev/ttyUSB0) | UART CLI |

### Notas importantes

- El script `run_jetson_native_capture.sh` tiene un bug de rutas: `SOFTWARE_DIR` apunta al raíz del proyecto, no a `software/`. Usar rutas absolutas via `RADAR_CFG`, `DCA_CFG`, `OUTPUT`.
- `captures/` y `*.bin` están en `.gitignore`.
- PYTHONPATH siempre necesario para correr módulos.
- Las pruebas de captura mostraron datos ADC consistentes (ruido ~200 LSB, sin saturación, ~2000 pkt/s).
