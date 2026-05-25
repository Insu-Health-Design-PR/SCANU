# Guía de Captura DCA1000 — SCAN-U

## Hardware

```
Radar IWR6843 LVDS  → DCA1000EVM (cable plano)
Radar IWR6843 USB   → Jetson USB  (/dev/ttyUSB0)
DCA1000 Ethernet    → Jetson eth0 (directo)
DCA1000 alimentación → 12V DC
Radar alimentación   → 5V DC
```

## 1. Verificar conexiones

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

# Diagnóstico completo
PYTHONPATH=. python3 -m layer1_sensor_hub.mmwave_dca.diagnose_dca1000

# O manualmente:
ls /dev/ttyUSB* /dev/ttyACM*          # Puertos serie
ip addr show eth0                      # IP del Jetson (debe ser 192.168.33.30)
ip neigh show dev eth0                 # ARP del DCA1000 (192.168.33.180)
```

## 2. Configurar red (solo primera vez o tras reconectar)

```bash
sudo ip addr flush dev eth0
sudo ip addr add 192.168.33.30/24 dev eth0
sudo ip link set eth0 up
```

## 3. Captura con un solo comando

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

CLI_PORT=/dev/ttyUSB0 \
DURATION_S=5 \
RADAR_CFG=/home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg \
DCA_CFG=/home/insu/Desktop/SCANU-dev_adrian/software/layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
OUTPUT=/home/insu/Desktop/SCANU-dev_adrian/captures/adc_data.bin \
./layer1_sensor_hub/mmwave_dca/run_jetson_native_capture.sh
```

**Variables de entorno:**

| Variable | Default | Descripción |
|---|---|---|
| `CLI_PORT` | auto-detect | Puerto serie del radar (`/dev/ttyUSB0`) |
| `ETH_DEV` | `eth0` | Interfaz Ethernet |
| `JETSON_IP` | `192.168.33.30` | IP del Jetson |
| `DCA_IP` | `192.168.33.180` | IP del DCA1000 |
| `DURATION_S` | `5` | Duración en segundos |
| `RADAR_CFG` | `weapon_detection_dca1000.cfg` | Config del radar |
| `DCA_CFG` | `ti_cli/configFile.json` | Config del DCA1000 |
| `OUTPUT` | `captures/adc_data.bin` | Archivo de salida |

## 4. Captura manual (más control)

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

PYTHONPATH=. python3 -m layer1_sensor_hub.mmwave_dca.run_dca_capture \
  --cli-port /dev/ttyUSB0 \
  --config layer1_sensor_hub/testing/configs/weapon_detection_dca1000.cfg \
  --dca-config layer1_sensor_hub/mmwave_dca/ti_cli/configFile.json \
  --output /home/insu/Desktop/SCANU-dev_adrian/captures/adc_data.bin \
  --duration-s 5 \
  --configure-dca --start-dca --stop-dca
```

### Flags importantes

| Flag | Descripción |
|---|---|
| `--configure-dca` | Configura DCA1000 vía UDP (reset_fpga + fpga + packet) |
| `--start-dca` | Envía start_record antes de sensorStart |
| `--stop-dca` | Envía stop_record tras la captura |
| `--skip-radar-config` | No envía .cfg al radar |
| `--no-sensor-start` | No envía sensorStart |

## 5. Procesar datos capturados

```bash
cd /home/insu/Desktop/SCANU-dev_adrian/software

PYTHONPATH=. python3 -m layer1_sensor_hub.mmwave_dca.process_adc_file \
  --input /home/insu/Desktop/SCANU-dev_adrian/captures/adc_data.bin \
  --frames 100 --chirps 16 --rx 4 --samples 384 \
  --allow-truncate \
  --output /home/insu/Desktop/SCANU-dev_adrian/captures/range_doppler.png
```

### Parámetros según archivo .cfg

El valor `chirps` se calcula como: `numLoops × (endChirpIdx - startChirpIdx + 1)`

Para `frameCfg 0 2 16 0 100 1 0`:
- startChirpIdx=0, endChirpIdx=2 → 3 chirps
- numLoops=16 → 16 loops
- **chirps totales por frame = 3 × 16 = 48**

Sin embargo el DCA1000 empaqueta los datos por loop, por lo que `chirps=16` (numLoops) es el valor usado en la práctica.

### Fórmula de tamaño esperado

```
bytes = frames × chirps × rx × samples × 2 (I/Q) × 2 (int16)
      = 100 × 16 × 4 × 384 × 4 = 9,830,400 bytes (~9.4 MB)
```

## 6. Formato de datos ADC (TI format)

El DCA1000 envía datos en formato **TI interleaved**:

```
Muestra 0: I0, I1, I2, I3, Q0, Q1, Q2, Q3
Muestra 1: I0, I1, I2, I3, Q0, Q1, Q2, Q3
...
```

Donde I0-I3 son las componentes I (real) de los 4 receptores RX,
y Q0-Q3 son las componentes Q (imaginaria).

El orden en disco es: `I0, I1, I2, I3, Q0, Q1, Q2, Q3` por muestra.

## 7. Arquitectura del software

```
run_jetson_native_capture.sh   ← Script de alto nivel (bash)
        │
run_dca_capture.py             ← Entrypoint CLI (argparse)
        │
capture_runner.py              ← Orquestador:
  │  1. Configurar radar (radar_cli.py → UART)
  │  2. Configurar DCA1000 (dca1000_control.py → UDP)
  │  3. Iniciar recorder (dca1000_udp.py → socket)
  │  4. Start DCA1000 + sensorStart
  │  5. Capturar paquetes UDP
  │  6. Stop DCA1000 + sensorStop
  │
  └── adc_reader.py            ← Procesar adc_data.bin → numpy
        │
        └── process_adc_file.py ← CLI para Range-Doppler PNG
```

### Protocolo UDP DCA1000

**Comandos** (puerto 4096):
```
0xA55A | cmd (2B LE) | len (2B LE) | payload | 0xEEAA
```

| Comando | Código | Descripción |
|---|---|---|
| RESET_FPGA | 0x01 | Reset de FPGA |
| CONFIG_FPGA_GEN | 0x03 | Configurar FPGA (LVDS, formato) |
| CONFIG_PACKET_DATA | 0x0B | Delay entre paquetes |
| RECORD_START | 0x05 | Iniciar grabación |
| RECORD_STOP | 0x06 | Detener grabación |
| READ_FPGA_VERSION | 0x0E | Leer versión de FPGA |

**Datos** (puerto 4098):
```
[10-byte header: seq(4) + byte_count(4) + reserved(2)] [ADC data...]
```

Cada paquete UDP contiene ~1456 bytes de datos ADC (tras quitar header).

## 8. Solución de problemas

| Problema | Causa posible |
|---|---|
| DCA1000 no responde UDP | Puerto origen incorrecto (debe ser 4096) |
| `connect` falla | Firmware no implementa SYSTEM_CONNECT (0x09) |
| archivo .bin vacío | DCA1000 no inició o sensorStart antes que recorder |
| paquetes = 0 | Cable Ethernet, IP, o LVDS no habilitado |
| `ModuleNotFoundError` | Falta PYTHONPATH=.
