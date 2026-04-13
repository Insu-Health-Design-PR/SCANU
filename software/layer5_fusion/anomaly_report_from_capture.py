#!/usr/bin/env python3
"""CLI: fused anomaly report from a raw capture JSON (mmWave + Layer 4 thermal)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from layer5_fusion.capture_fusion import main

if __name__ == "__main__":
    raise SystemExit(main())
