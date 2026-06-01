"""L1/L2 -> Layer 6 fusion input adapter — weapon-detection edition.

Consumes the enriched mmWave features produced by the weapon-optimised
Layer 1/2 pipeline (micro-Doppler, RCS proxy, weapon-confidence tracker,
azimuth-static peak) and produces a weighted fusion score that prioritises
weapon-like signatures.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from software.settings import MMWAVE_MAX_POINTS, THERMAL_ALPHA, WEAPON_WEIGHT
from .models import FusionInputContract


class L1L2FusionAdapter:
    """Builds a weighted fusion score from Layer 1/2 signals with weapon priors."""

    def __init__(
        self,
        *,
        mmwave_max_points: int = MMWAVE_MAX_POINTS,
        thermal_alpha: float = THERMAL_ALPHA,
        weapon_weight: float = WEAPON_WEIGHT,
    ) -> None:
        self._mmwave_max_points = max(1, int(mmwave_max_points))
        self._thermal_alpha = float(np.clip(thermal_alpha, 0.001, 1.0))
        self._thermal_baseline_mean: float | None = None
        self._weapon_weight = float(np.clip(weapon_weight, 0.0, 1.0))

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    # ── thermal ────────────────────────────────────────────────────────

    def _thermal_score(self, thermal_frame_bgr: Any, direct_value: Any = None) -> float:
        if direct_value is not None:
            try:
                return float(np.clip(float(direct_value), 0.0, 1.0))
            except Exception:
                return 0.0
        if thermal_frame_bgr is None:
            return 0.0
        arr = np.asarray(thermal_frame_bgr)
        if arr.size == 0:
            return 0.0
        mean_val = float(np.mean(arr.astype(np.float32)))
        if self._thermal_baseline_mean is None:
            self._thermal_baseline_mean = mean_val
        baseline = float(self._thermal_baseline_mean)
        delta = abs(mean_val - baseline)
        self._thermal_baseline_mean = (1.0 - self._thermal_alpha) * baseline + self._thermal_alpha * mean_val
        return float(np.clip(delta / 35.0, 0.0, 1.0))

    # ── weapon-specific scoring ────────────────────────────────────────

    def _weapon_score(
        self,
        *,
        weapon_confidence: float = 0.0,
        micro_doppler_bw: float = 0.0,
        doppler_centroid: float = 0.0,
        azimuth_static_peak: float = 0.0,
        rcs_proxy_mean: float = 0.0,
        max_snr: float = 0.0,
        point_count: int = 0,
    ) -> float:
        components: list[float] = []

        wc = float(np.clip(weapon_confidence, 0.0, 1.0))
        components.append(wc * 0.35)

        if micro_doppler_bw > 1e-6:
            bw_norm = float(np.clip(micro_doppler_bw * 4.0, 0.0, 1.0))
        else:
            bw_norm = 0.0
        components.append(bw_norm * 0.20)

        az_norm = float(np.clip(azimuth_static_peak / 50.0, 0.0, 1.0))
        components.append(az_norm * 0.15)

        snr_norm = float(np.clip(max_snr / 20.0, 0.0, 1.0))
        components.append(snr_norm * 0.15)

        if rcs_proxy_mean > 1e-6 and point_count > 0:
            rcs_norm = float(np.clip(np.log10(rcs_proxy_mean + 1.0) / 4.0, 0.0, 1.0))
        else:
            rcs_norm = 0.0
        components.append(rcs_norm * 0.15)

        return float(np.clip(sum(components), 0.0, 1.0))

    # ── main adapt ─────────────────────────────────────────────────────

    def adapt(
        self,
        raw_inputs: Any,
        *,
        radar_id: str = "radar_main",
        now_ms: float | None = None,
    ) -> FusionInputContract:
        if isinstance(raw_inputs, FusionInputContract):
            return raw_inputs

        ts = float(now_ms if now_ms is not None else time.time() * 1000.0)
        frame_number = int(self._get(raw_inputs, "frame_number", 0))
        frame_ts = self._get(raw_inputs, "timestamp_ms", ts)

        mmwave_frame = self._get(raw_inputs, "mmwave_frame")
        presence_frame = self._get(raw_inputs, "presence_frame")
        thermal_frame = self._get(raw_inputs, "thermal_frame_bgr")

        if mmwave_frame is None:
            mmwave_frame = self._get(raw_inputs, "layer2_processed")

        points = self._get(mmwave_frame, "points", []) if mmwave_frame is not None else []
        point_count = len(points) if points is not None else 0
        mmwave_score = float(np.clip(point_count / float(self._mmwave_max_points), 0.0, 1.0))

        presence_raw = float(self._get(presence_frame, "presence_raw", 0.0) or 0.0)
        motion_raw = float(self._get(presence_frame, "motion_raw", 0.0) or 0.0)
        presence_score = float(np.clip(presence_raw, 0.0, 1.0))
        motion_score = float(np.clip(motion_raw, 0.0, 1.0))

        thermal_direct = self._get(raw_inputs, "thermal_presence", None)
        thermal_score = self._thermal_score(thermal_frame, direct_value=thermal_direct)

        gun_detected = bool(self._get(raw_inputs, "gun_detected", False))
        unsafe_score_l4 = float(self._get(raw_inputs, "unsafe_score_l4", 0.0) or 0.0)

        weapon_track = self._get(mmwave_frame, "weapon_track") if mmwave_frame is not None else None
        weapon_confidence = float(self._get(weapon_track or {}, "weapon_confidence", 0.0) or 0.0)
        micro_doppler_bw = float(self._get(mmwave_frame, "micro_doppler_bw", 0.0) or 0.0)
        doppler_centroid = float(self._get(mmwave_frame, "doppler_centroid", 0.0) or 0.0)
        azimuth_static_peak = float(self._get(mmwave_frame, "azimuth_static_peak", 0.0) or 0.0)
        rcs_proxy_mean = float(self._get(mmwave_frame, "rcs_proxy_mean", 0.0) or 0.0)

        max_snr_value = 0.0
        if points and isinstance(points, list) and len(points) > 0:
            snr_values = [
                float(self._get(p, "snr", 0.0) or 0.0)
                for p in points
                if isinstance(p, dict)
            ]
            if snr_values:
                max_snr_value = max(snr_values)

        weapon_score = self._weapon_score(
            weapon_confidence=weapon_confidence,
            micro_doppler_bw=micro_doppler_bw,
            doppler_centroid=doppler_centroid,
            azimuth_static_peak=azimuth_static_peak,
            rcs_proxy_mean=rcs_proxy_mean,
            max_snr=max_snr_value,
            point_count=point_count,
        )

        trigger_score = float(max(
            mmwave_score,
            presence_score,
            motion_score,
            thermal_score,
            weapon_score * 0.7,
        ))
        trigger_score = float(np.clip(trigger_score, 0.0, 1.0))

        sensor_weight = max(0.0, 1.0 - self._weapon_weight)

        anomaly_score = float(
            np.clip(
                sensor_weight * (
                    0.45 * mmwave_score
                    + 0.20 * presence_score
                    + 0.20 * motion_score
                    + 0.15 * thermal_score
                )
                + self._weapon_weight * weapon_score,
                0.0,
                1.0,
            )
        )

        l4_boost = 0.0
        if gun_detected:
            l4_boost = max(0.45, unsafe_score_l4 * 0.70)
        elif unsafe_score_l4 > 0.30:
            l4_boost = unsafe_score_l4 * 0.30
        anomaly_score = float(np.clip(anomaly_score + l4_boost, 0.0, 1.0))

        fused_override = self._get(raw_inputs, "fused_score", None)
        if fused_override is not None:
            try:
                fused_score = float(np.clip(float(fused_override), 0.0, 1.0))
            except Exception:
                fused_score = anomaly_score
        else:
            fused_score = anomaly_score

        signals_available = 1
        signals_available += 1 if presence_frame is not None else 0
        signals_available += 1 if thermal_frame is not None or thermal_direct is not None else 0
        signals_available += 1 if weapon_confidence > 0.05 else 0
        signals_available += 1 if gun_detected else 0
        confidence = float(np.clip(
            0.30 + 0.15 * signals_available + 0.35 * max(0.0, mmwave_score) + 0.20 * weapon_score,
            0.0,
            1.0,
        ))

        return FusionInputContract(
            frame_number=frame_number,
            timestamp_ms=float(frame_ts),
            radar_id=str(self._get(raw_inputs, "radar_id", radar_id) or radar_id),
            fused_score=fused_score,
            confidence=confidence,
            trigger_score=trigger_score,
            anomaly_score=anomaly_score,
            source_mode="weapon_l1_l2",
            evidence={
                "mmwave_score": mmwave_score,
                "presence_score": presence_score,
                "motion_score": motion_score,
                "thermal_score": thermal_score,
                "weapon_score": weapon_score,
                "weapon_confidence": weapon_confidence,
                "micro_doppler_bw": micro_doppler_bw,
                "doppler_centroid": doppler_centroid,
                "azimuth_static_peak": azimuth_static_peak,
                "rcs_proxy_mean": rcs_proxy_mean,
                "max_snr": max_snr_value,
                "signals_available": float(signals_available),
                "point_count": float(point_count),
                "gun_detected": float(gun_detected),
                "unsafe_score_l4": unsafe_score_l4,
            },
        )
