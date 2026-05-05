"""Layer 5: Multi-Sensor Fusion.

Produces a weighted `FusionInputContract` from Layer 1-4 sensor signals,
prioritising weapon-specific features (micro-Doppler, RCS proxy, weapon
confidence from the mmWave tracker) alongside thermal presence and
camera-based gun detection.
"""

from .fusion_adapter import L1L2FusionAdapter
from .models import FusionInputContract

__all__ = [
    "L1L2FusionAdapter",
    "FusionInputContract",
]
