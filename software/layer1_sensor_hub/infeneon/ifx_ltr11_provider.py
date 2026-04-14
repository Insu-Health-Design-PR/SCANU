"""Minimal Infineon BGT60LTR11AIP provider via `ifxradarsdk`."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(slots=True)
class IfxLtr11ProviderConfig:
    """Optional configuration overrides for LTR11."""

    rf_frequency_hz: Optional[int] = None
    num_of_samples: Optional[int] = None
    detector_threshold: Optional[int] = None
    prt: Optional[int] = None
    pulse_width: Optional[int] = None
    tx_power_level: Optional[int] = None
    rx_if_gain: Optional[int] = None
    aprt_factor: Optional[int] = None
    hold_time: Optional[int] = None
    disable_internal_detector: Optional[bool] = None


class IfxLtr11PresenceProvider:
    """PresenceProvider backed by Infineon `DeviceLtr11`."""

    def __init__(self, uuid: str | None = None, config: IfxLtr11ProviderConfig | None = None) -> None:
        # Lazy import keeps this module importable without SDK installed.
        from ifxradarsdk.ltr11 import DeviceLtr11

        self._dev = DeviceLtr11(uuid=uuid)
        self._started = False
        self._prev_frame: np.ndarray | None = None
        self._power_baseline: float | None = None
        self._baseline_warmup_left = 20
        self._presence_ema = 0.0
        self._ema_alpha = 0.25
        self._active_hist: deque[bool] = deque(maxlen=40)
        self._motion_flag_hist: deque[bool] = deque(maxlen=40)
        self._motion_score_hist: deque[float] = deque(maxlen=40)
        self._avg_power_hist: deque[float] = deque(maxlen=40)
        self.last_meta: dict | None = None

        cfg = self._dev.get_config_defaults()
        if config is not None:
            if config.rf_frequency_hz is not None:
                cfg.rf_frequency_Hz = int(config.rf_frequency_hz)
            if config.num_of_samples is not None:
                cfg.num_of_samples = int(config.num_of_samples)
            if config.detector_threshold is not None:
                cfg.detector_threshold = int(config.detector_threshold)
            if config.prt is not None:
                cfg.prt = int(config.prt)
            if config.pulse_width is not None:
                cfg.pulse_width = int(config.pulse_width)
            if config.tx_power_level is not None:
                cfg.tx_power_level = int(config.tx_power_level)
            if config.rx_if_gain is not None:
                cfg.rx_if_gain = int(config.rx_if_gain)
            if config.aprt_factor is not None:
                cfg.aprt_factor = int(config.aprt_factor)
            if config.hold_time is not None:
                cfg.hold_time = int(config.hold_time)
            if config.disable_internal_detector is not None:
                cfg.disable_internal_detector = bool(config.disable_internal_detector)

        self._dev.set_config(cfg)

    def start(self) -> None:
        if not self._started:
            self._dev.start_acquisition()
            self._started = True

    def close(self) -> None:
        try:
            if self._started:
                self._dev.stop_acquisition()
        finally:
            self._started = False
            close_fn = getattr(self._dev, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
                return
            private_close = getattr(self._dev, "_close", None)
            if callable(private_close):
                try:
                    private_close()
                except Exception:
                    pass

    def read_sample(self) -> tuple[float, float, float]:
        """Returns `(presence_raw, motion_raw, distance_m)` for one sample."""

        self.start()
        frame, metadata = self._dev.get_next_frame(timeout_ms=2000)

        arr = np.asarray(frame)
        mag = np.abs(arr)
        signal_rms = float(np.sqrt(np.mean(mag * mag))) if mag.size else 0.0

        motion_energy = 0.0
        if self._prev_frame is not None and self._prev_frame.shape == arr.shape:
            diff = arr - self._prev_frame
            dmag = np.abs(diff)
            motion_energy = float(np.sqrt(np.mean(dmag * dmag))) if dmag.size else 0.0
        self._prev_frame = arr.copy()

        avg_power = float(getattr(metadata, "avg_power", 0.0))
        if self._power_baseline is None:
            self._power_baseline = max(avg_power, 1e-6)

        if self._baseline_warmup_left > 0:
            self._power_baseline = 0.7 * self._power_baseline + 0.3 * max(avg_power, 1e-6)
            self._baseline_warmup_left -= 1
        else:
            # Slow baseline tracking for long sessions and mild ambient drift.
            self._power_baseline = 0.995 * self._power_baseline + 0.005 * max(avg_power, 1e-6)

        baseline = max(self._power_baseline, 1e-6)
        power_delta = max(0.0, avg_power - baseline)
        power_score = float(np.clip(power_delta / (0.25 * baseline + 1e-6), 0.0, 1.0))

        active = bool(getattr(metadata, "active", False))
        motion_flag = bool(getattr(metadata, "motion", False))
        motion_score = float(np.clip(motion_energy / (signal_rms + 1e-6), 0.0, 1.0))

        self._active_hist.append(active)
        self._motion_flag_hist.append(motion_flag)
        self._motion_score_hist.append(motion_score)
        self._avg_power_hist.append(avg_power)

        active_ratio = 1.0 if active else 0.0
        motion_flag_ratio = 1.0 if motion_flag else 0.0
        mean_motion_score = motion_score
        power_cv = 0.0
        active_stuck_high = False
        if self._active_hist:
            active_ratio = float(np.mean(np.asarray(self._active_hist, dtype=np.float32)))
            motion_flag_ratio = float(np.mean(np.asarray(self._motion_flag_hist, dtype=np.float32)))
            mean_motion_score = float(np.mean(np.asarray(self._motion_score_hist, dtype=np.float32)))
            p_arr = np.asarray(self._avg_power_hist, dtype=np.float32)
            p_mean = float(np.mean(p_arr)) if p_arr.size else 0.0
            p_std = float(np.std(p_arr)) if p_arr.size else 0.0
            power_cv = p_std / max(1e-6, p_mean)
            active_stuck_high = (
                len(self._active_hist) >= 20
                and active_ratio > 0.95
                and motion_flag_ratio < 0.10
                and mean_motion_score < 0.20
                and power_cv < 0.02
            )

        active_weight = 0.55
        if active_stuck_high:
            # Some boards/firmware report `active=True` almost always.
            # Down-weight active to avoid a permanently high presence floor.
            active_weight = 0.10
        elif active_ratio < 0.05:
            # If active is almost always false, still keep a small influence.
            active_weight = 0.20

        power_weight = 0.30
        motion_weight = 1.0 - active_weight - power_weight
        active_score = 1.0 if active else 0.0

        # Presence should remain meaningful for quiet subjects, not only motion.
        presence_raw_instant = float(
            np.clip(
                active_weight * active_score + power_weight * power_score + motion_weight * motion_score,
                0.0,
                1.0,
            )
        )
        self._presence_ema = (1.0 - self._ema_alpha) * self._presence_ema + self._ema_alpha * presence_raw_instant
        presence_raw = float(np.clip(self._presence_ema, 0.0, 1.0))

        motion_raw = max(1.0 if motion_flag else 0.0, motion_score)
        # LTR11 metadata does not expose direct distance.
        distance_m = -1.0

        self.last_meta = {
            "avg_power": avg_power,
            "power_baseline": baseline,
            "active": active,
            "motion": motion_flag,
            "direction": bool(getattr(metadata, "direction", False)),
            "num_samples": int(arr.size),
            "signal_rms": signal_rms,
            "motion_energy": motion_energy,
            "power_score": power_score,
            "motion_score": motion_score,
            "active_ratio": active_ratio,
            "motion_flag_ratio": motion_flag_ratio,
            "mean_motion_score": mean_motion_score,
            "power_cv": power_cv,
            "active_stuck_high": active_stuck_high,
            "active_weight": active_weight,
            "presence_raw_instant": presence_raw_instant,
        }
        return presence_raw, motion_raw, distance_m
