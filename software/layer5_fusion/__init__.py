"""Layer 5: Multi-Sensor Fusion.
 
Produces a weighted `FusionInputContract` from Layer 1-4 sensor signals,
prioritising weapon-specific features (micro-Doppler, RCS proxy, weapon
confidence from the mmWave tracker) alongside thermal presence and
camera-based gun detection.
"""

from .deterministic_fusion import DeterministicFusionAdapter
from .fusion_adapter import L1L2FusionAdapter
from .kalman_tracker import FusedTrack, KalmanFilterTracker
from .models import FusionInputContract

__all__ = [
    "DeterministicFusionAdapter",
    "L1L2FusionAdapter",
    "FusionInputContract",
    "KalmanFilterTracker",
    "FusedTrack",
]
