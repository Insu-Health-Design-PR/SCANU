"""Centralised constants and paths for all layers."""

from __future__ import annotations

from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────
COLLECTING_DATA_DIR = Path.home() / "Desktop" / "collecting_data"
DEFAULT_MMWAVE_CONFIG = "layer1_sensor_hub/examples/configs/weapon_detection_dca1000.cfg"

# ── Devices ─────────────────────────────────────────────────────
DEFAULT_CLI_PORT: str = ""                             # auto-detect
DEFAULT_DATA_PORT: str = ""                            # auto-detect
DEFAULT_THERMAL_DEVICE: int | str = 0
DEFAULT_WEBCAM_DEVICE: int | str = 0

# ── DCA1000 ────────────────────────────────────────────────────
DCA1000_HOST_IP = "192.168.33.30"
DCA1000_DEVICE_IP = "192.168.33.180"
DCA1000_CONFIG_PORT = 4096
DCA1000_DATA_PORT = 4098
MIMO_LOOPS = 16
MIMO_NUM_TX = 3

# ── CFAR (Layer 1 / Layer 2) ──────────────────────────────────
CFAR_THRESHOLD_SCALE = 3.0        # MIMO default
CFAR_NOISE_FLOOR_OFFSET_DB = 1.5
CFAR_GUARD = 1
CFAR_TRAIN = 2
NUM_RANGE_BINS = 256

# Legacy defaults (UART / TLV pipeline)
LEGACY_CFAR_THRESHOLD_SCALE = 8.0
LEGACY_CFAR_NOISE_FLOOR_OFFSET_DB = 3.0

# ── DBSCAN (Layer 2) ──────────────────────────────────────────
DBSCAN_EPS = 0.4
DBSCAN_MIN_SAMPLES = 3

# ── Kalman filter (Layer 5) ───────────────────────────────────
KF_DT = 0.05
KF_MAX_AGE = 30
KF_ASSOCIATION_DISTANCE = 1.5      # metres

# ── Fusion (Layer 5) ──────────────────────────────────────────
WEAPON_WEIGHT = 0.50
THERMAL_ALPHA = 0.05
MMWAVE_MAX_POINTS = 12

# ── Layer 3 ───────────────────────────────────────────────────
MMWAVE_WEAPON_THRESH = 0.3
