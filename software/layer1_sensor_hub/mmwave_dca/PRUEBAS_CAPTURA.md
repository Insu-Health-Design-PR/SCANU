# Pruebas de Captura DCA1000 — Resultados

## Resumen

Se ejecutaron 3 capturas de prueba con diferentes duraciones para verificar el funcionamiento del DCA1000 y caracterizar el flujo de datos.

## Configuración utilizada

| Parámetro | Valor |
|---|---|
| Radar | IWR6843 |
| Config radar | `weapon_detection_dca1000.cfg` |
| Config DCA1000 | `ti_cli/configFile.json` |
| Modo captura | ethernetStream |
| Puerto radar | `/dev/ttyUSB0` |
| IP Jetson | `192.168.33.30` |
| IP DCA1000 | `192.168.33.180` |
| Puerto config | `4096` |
| Puerto datos | `4098` |

### Parámetros del radar (weapon_detection_dca1000.cfg)

| Parámetro | Valor |
|---|---|
| profileCfg samples | 384 |
| profileCfg rate | 2000 kHz |
| RX activos | 4 |
| Chirps por frame | 3 perfiles × 16 loops = 48 chirps total |
| frameCfg frames | 100 |
| frameCfg periodicity | 100ms |
| lvdsStreamCfg | habilitado (lane=1, format=0) |
| dataFormatMode | 3 (complex 2x) |

## Resultados

### Tabla comparativa

| Captura | Duración | Paquetes | Tamaño | Tasa (pkt/s) | Tasa (MB/s) |
|---|---|---|---|---|---|
| test_3s | 3s | 5,965 | 8.3 MB | 1,988 | 2.77 |
| test_5s | 5s | 10,024 | 14 MB | 2,005 | 2.79 |
| test_10s | 10s | 20,151 | 28 MB | 2,015 | 2.79 |

### Consistencia

Los resultados son altamente consistentes entre las 3 capturas:

- **Tasa de paquetes**: ~2,000 paquetes UDP por segundo (variación <1.4%)
- **Bytes por paquete**: **1456 fijos** (medido exactamente en los 3 casos)
- **Tasa de datos**: ~2.79 MB/s sostenidos
- **Dinámica de señal**: rango ±4000 int16, media ~0, desviación ~205 (ADC ruidoso, sin saturación)

## Formato de datos

### Estructura del paquete UDP (puerto 4098)

```
┌─────────────────────────────────────────────┐
│ Header (10 bytes)                            │
│  - sequence_number (4B uint32 LE)            │
│  - byte_count (4B uint32 LE)                 │
│  - reserved (2B)                             │
├─────────────────────────────────────────────┤
│ ADC Data (~1456 bytes)                       │
│  = 728 valores int16                         │
└─────────────────────────────────────────────┘
```

### Formato TI interleaved (dataFormatMode=3)

Para 4 receptores (RX0..RX3), cada sample produce 8 valores int16:

```
Sample 0: I0, I1, I2, I3, Q0, Q1, Q2, Q3  (8 int16 = 16 bytes)
Sample 1: I0, I1, I2, I3, Q0, Q1, Q2, Q3
...
Sample N: ...
```

Esto se conoce como "TI format" (alternativamente "IQ format" sería I,Q,I,Q...).

### Dimensiones esperadas

| Dimensión | Valor | Cálculo |
|---|---|---|
| Samples por chirp | 384 | profileCfg |
| RX | 4 | channelCfg |
| Chirps por frame | 16 | numLoops (frameCfg) |
| Frames | 100 | numFrames (frameCfg) |
| **Bytes total esperados** | **9,830,400** | 100 × 16 × 4 × 384 × 2 × 2 |

### Empaquetado en UDP

- 1456 bytes de payload = 728 int16 por paquete
- 728 / (4 RX × 2 I/Q) = 91 samples por paquete
- 384 samples / 91 samples = ~4.22 paquetes por chirp (el DCA1000 fragmenta entre chirps)

## Variaciones entre capturas

### Efecto de la duración

| Duración | Frames completos | Paquetes | Observación |
|---|---|---|---|
| 3s | 88 | 5,965 | Archivo truncado: 8.68M < 9.83M (100 frames) |
| 5s | 148 | 10,024 | Archivo excede 100 frames → truncado a 100 |
| 10s | 298 | 20,151 | Archivo excede 100 frames → truncado a 100 |

Con 100ms por frame y 16 chirps × 384 samples × 4 RX:
- En 3 segundos → ~30 frames esperados, pero el DCA captura hasta que se detiene
- El parámetro `frameCfg numFrames=100` no limita cuando se usa `sensorStart` tras el DCA1000
- La duración real la controla el timeout de captura (`--duration-s`)

### Calidad de la señal

```
          test_3s     test_5s     test_10s
Min:      -4076       -4083       -4114
Max:       3955        3974        4014
Mean:       0.8         0.9         1.0
Std:      204.7       203.7       209.9
```

- Ruido de fondo ~200 LSB (esperado para ADC de 14-16 bits con ganancia)
- Sin saturación (nunca alcanza ±32768)
- Media cercana a 0 (DC offset mínimo)
- Señales consistentes entre capturas

## Problemas encontrados y soluciones

### 1. DCA1000 no respondía a comandos UDP

**Causa**: El firmware del DCA1000 en esta placa no implementa el comando `SYSTEM_CONNECT` (0x09), y la librería lo enviaba primero.

**Solución**: En `dca1000_control.py`:
- Cambiar `connect_first=True` → `False`
- Bindear socket al puerto de configuración (4096) en vez de puerto efímero (0)
- Validar respuesta por footer (0xEEAA) en vez de verificar bytes de estado

### 2. Ruta incorrecta en script shell

**Causa**: `run_jetson_native_capture.sh` calculaba `SOFTWARE_DIR` como el proyecto raíz, no como `software/`.

**Solución**: Pasar rutas absolutas via variables de entorno, o usar PYTHONPATH.

### 3. `ModuleNotFoundError: No module named 'layer1_sensor_hub'`

**Causa**: Python no encuentra los módulos locales sin PYTHONPATH.

**Solución**: `export PYTHONPATH=/home/insu/Desktop/SCANU-dev_adrian/software:$PYTHONPATH`

## Archivos generados

```
captures/
├── adc_data.bin          (14M)  Última captura con run_jetson_native_capture.sh
├── test_3s.bin           (8.3M) Captura de 3 segundos
├── test_5s.bin           (14M)  Captura de 5 segundos
├── test_10s.bin          (28M)  Captura de 10 segundos
├── test_5s_rd.png               Range-Doppler de test_5s
└── test_10s_rd.png              Range-Doppler de test_10s
```
