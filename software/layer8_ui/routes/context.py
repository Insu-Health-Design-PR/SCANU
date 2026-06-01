"""Shared context for route modules."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from layer1_sensor_hub.mmwave import MovementTrailTracker


@dataclass
class RouterContext:
    """Dependencies injected into each route module by ``build_router``."""

    layer8_dir: Path
    thermal_stream: Any
    webcam_stream: Any
    layer6_orchestrator: Optional[Any] = None
    layer7_bridge: Optional[Any] = None
    layer7_recent_alerts: deque[dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=200)
    )
    layer6_cache: dict[str, Any] = field(
        default_factory=lambda: {
            "ts_ms": 0.0,
            "event": None,
            "snapshot": None,
            "action_request": None,
        }
    )
    mmwave_trail_tracker: MovementTrailTracker = field(
        default_factory=lambda: MovementTrailTracker(max_trail_length=15)
    )
