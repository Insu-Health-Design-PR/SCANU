"""Multi-modal feature extraction: mmWave + RGB + Thermal → unified vector.

Extracts deterministic features from three sensors and fuses them into
a single feature vector for Layer 4 AI training or Layer 5 scoring.

Typical usage::

    extractor = MultiModalFeatureExtractor()
    features = extractor.extract(dca_result, rgb_frame, thermal_frame)
    vector = features.to_vector()  # 30-dim float32 array
    score = features.deterministic_score()  # 0-1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import cv2
import numpy as np


@dataclass
class MultiModalFeatures:
    """Feature vector from all three sensors."""

    # mmWave (DCA1000)
    zone_coherence_max: float = 0.0
    coherence_contrast: float = 0.0
    zone_phase_stability: float = 0.0
    pstab_contrast: float = 0.0
    zone_energy_ratio: float = 0.0
    n_cfar_detections_zone: float = 0.0
    n_cfar_detections_total: float = 0.0
    motion_energy: float = 0.0
    mmwave_weapon_score: float = 0.0

    # mmWave DCA1000 point cloud stats
    n_points_total: float = 0.0
    n_points_zone: float = 0.0
    mean_snr: float = 0.0
    max_snr: float = 0.0
    range_spread: float = 0.0

    # RGB visual
    rgb_mean_brightness: float = 0.0
    rgb_std_brightness: float = 0.0
    rgb_motion_magnitude: float = 0.0
    rgb_green_dominant: float = 0.0  # camouflage/green clothing
    rgb_skin_pct: float = 0.0
    rgb_waist_region_brightness: float = 0.0  # brightness in lower torso

    # Thermal
    thermal_mean: float = 0.0
    thermal_std: float = 0.0
    thermal_max: float = 0.0
    thermal_min: float = 0.0
    thermal_body_heat_pct: float = 0.0  # pixels above body temp threshold
    thermal_cold_spot_pct: float = 0.0  # cold pixels = potential metal
    thermal_waist_region_heat: float = 0.0  # heat in waist area

    # Cross-sensor
    mmwave_thermal_corr: float = 0.0  # correlation (if meaningful)
    any_sensor_active: float = 0.0

    def to_vector(self) -> np.ndarray:
        vals = [
            self.zone_coherence_max, self.coherence_contrast,
            self.zone_phase_stability, self.pstab_contrast,
            self.zone_energy_ratio, self.n_cfar_detections_zone,
            self.n_cfar_detections_total, self.motion_energy,
            self.mmwave_weapon_score,
            self.n_points_total, self.n_points_zone,
            self.mean_snr, self.max_snr, self.range_spread,
            self.rgb_mean_brightness, self.rgb_std_brightness,
            self.rgb_motion_magnitude, self.rgb_green_dominant,
            self.rgb_skin_pct, self.rgb_waist_region_brightness,
            self.thermal_mean, self.thermal_std,
            self.thermal_max, self.thermal_min,
            self.thermal_body_heat_pct, self.thermal_cold_spot_pct,
            self.thermal_waist_region_heat,
            self.mmwave_thermal_corr, self.any_sensor_active,
        ]
        return np.array(vals, dtype=np.float32)

    def deterministic_score(self) -> float:
        """Logic-based fusion score (0-1) for pre-AI deployment."""
        components: list[float] = []

        # mmWave coherence (high = metal)
        zc = float(np.clip((self.zone_coherence_max - 0.08) / 0.12, 0.0, 1.0))
        components.append(zc * 0.25)

        # mmWave contrast
        cc = float(np.clip((self.coherence_contrast - 0.60) / 1.0, 0.0, 1.0))
        components.append(cc * 0.20)

        # mmWave CFAR zone count
        cz = float(np.clip(self.n_cfar_detections_zone / 100.0, 0.0, 1.0))
        components.append(cz * 0.10)

        # Thermal cold spot (metal is cold)
        cold = float(np.clip(self.thermal_cold_spot_pct / 10.0, 0.0, 1.0))
        components.append(cold * 0.15)

        # Thermal waist region anomaly
        tw = float(np.clip((self.thermal_waist_region_heat - 0.30) / 0.30, 0.0, 1.0))
        components.append(tw * 0.10)

        # RGB skin percentage (less skin = more covered = suspicious)
        sk = float(np.clip(1.0 - self.rgb_skin_pct, 0.0, 1.0))
        components.append(sk * 0.05)

        # RGB waist brightness anomaly
        rw = float(np.clip((self.rgb_waist_region_brightness - 0.30) / 0.30, 0.0, 1.0))
        components.append(rw * 0.05)

        # Phase stability
        ps = float(np.clip((self.zone_phase_stability - 0.40) / 0.40, 0.0, 1.0))
        components.append(ps * 0.10)

        score = float(np.clip(sum(components), 0.0, 1.0))
        return score

    def to_evidence_dict(self) -> dict[str, float]:
        return {
            "zone_coherence_max": self.zone_coherence_max,
            "coherence_contrast": self.coherence_contrast,
            "zone_phase_stability": self.zone_phase_stability,
            "pstab_contrast": self.pstab_contrast,
            "n_cfar_detections_zone": self.n_cfar_detections_zone,
            "mmwave_weapon_score": self.mmwave_weapon_score,
            "n_points_zone": self.n_points_zone,
            "n_points_total": self.n_points_total,
            "mean_snr": self.mean_snr,
            "range_spread": self.range_spread,
            "thermal_cold_spot_pct": self.thermal_cold_spot_pct,
            "thermal_body_heat_pct": self.thermal_body_heat_pct,
            "thermal_waist_region_heat": self.thermal_waist_region_heat,
            "rgb_skin_pct": self.rgb_skin_pct,
            "rgb_waist_region_brightness": self.rgb_waist_region_brightness,
            "rgb_green_dominant": self.rgb_green_dominant,
            "deterministic_score": self.deterministic_score(),
        }


class MultiModalFeatureExtractor:
    """Extract features from mmWave + RGB + Thermal for weapon detection."""

    # Simple skin colour range in HSV
    SKIN_LOWER = np.array([0, 20, 70], dtype=np.uint8)
    SKIN_UPPER = np.array([20, 150, 255], dtype=np.uint8)

    def extract(
        self,
        mmwave_result: Any = None,
        rgb_frame: Optional[np.ndarray] = None,
        thermal_frame: Optional[np.ndarray] = None,
    ) -> MultiModalFeatures:
        f = MultiModalFeatures()

        # ── mmWave ──────────────────────────────────────────────────
        if mmwave_result is not None:
            feats = getattr(mmwave_result, "features", {})
            pc = getattr(mmwave_result, "point_cloud", None)

            f.zone_coherence_max = float(feats.get("zone_coherence_max", 0.0))
            f.coherence_contrast = float(feats.get("coherence_contrast", 0.0))
            f.zone_phase_stability = float(feats.get("zone_phase_stability", 0.0))
            f.pstab_contrast = float(feats.get("pstab_contrast", 0.0))
            f.zone_energy_ratio = float(feats.get("zone_energy_ratio", 0.0))
            f.n_cfar_detections_zone = float(feats.get("n_cfar_detections_zone", 0.0))
            f.n_cfar_detections_total = float(feats.get("n_cfar_detections", 0.0))
            f.motion_energy = float(feats.get("motion_energy", 0.0))
            f.mmwave_weapon_score = float(getattr(mmwave_result, "weapon_score", 0.0))

            if pc is not None and len(pc) > 0:
                f.n_points_total = float(len(pc))
                # point_cloud columns: [range_bin, doppler_bin, angle, snr, zone_flag]
                has_zone_flag = pc.shape[1] >= 5
                if has_zone_flag:
                    zone_mask = pc[:, 4] > 0.5
                    zone_pts = pc[zone_mask]
                else:
                    zone_pts = pc
                f.n_points_zone = float(len(zone_pts))
                f.mean_snr = float(pc[:, 3].mean()) if pc.shape[1] >= 4 else 0.0
                f.max_snr = float(pc[:, 3].max()) if pc.shape[1] >= 4 else 0.0
                if len(zone_pts) > 1:
                    f.range_spread = float(zone_pts[:, 1].max() - zone_pts[:, 1].min()) * 0.013

        # ── RGB ─────────────────────────────────────────────────────
        if rgb_frame is not None and rgb_frame.size > 0:
            gray = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2HSV)

            f.rgb_mean_brightness = float(gray.mean() / 255.0)
            f.rgb_std_brightness = float(gray.std() / 255.0)

            # Green dominance (camouflage / green clothing)
            green_ch = rgb_frame[:, :, 1].astype(np.float32)
            red_ch = rgb_frame[:, :, 2].astype(np.float32)
            blue_ch = rgb_frame[:, :, 0].astype(np.float32)
            green_dom = (green_ch > red_ch + 10) & (green_ch > blue_ch + 10)
            f.rgb_green_dominant = float(green_dom.mean())

            # Skin colour percentage (HSV-based)
            skin_mask = cv2.inRange(hsv, self.SKIN_LOWER, self.SKIN_UPPER)
            f.rgb_skin_pct = float(skin_mask.mean() / 255.0)

            # Waist region (lower third of frame)
            h, w = gray.shape[:2]
            waist = gray[int(h * 0.55):int(h * 0.80), :]
            f.rgb_waist_region_brightness = float(waist.mean() / 255.0) if waist.size > 0 else 0.0

        # ── Thermal ─────────────────────────────────────────────────
        if thermal_frame is not None and thermal_frame.size > 0:
            if len(thermal_frame.shape) == 3:
                gray_th = cv2.cvtColor(thermal_frame, cv2.COLOR_BGR2GRAY)
            else:
                gray_th = thermal_frame

            f.thermal_mean = float(gray_th.mean() / 255.0)
            f.thermal_std = float(gray_th.std() / 255.0)
            f.thermal_max = float(gray_th.max() / 255.0)
            f.thermal_min = float(gray_th.min() / 255.0)

            # Body heat pixels (above 60% of thermal range)
            body_mask = gray_th > int(0.60 * 255)
            f.thermal_body_heat_pct = float(body_mask.mean())

            # Cold spot = potential metal (below 30% of thermal range)
            cold_mask = gray_th < int(0.30 * 255)
            f.thermal_cold_spot_pct = float(cold_mask.mean())

            # Waist region temperature
            h, w = gray_th.shape[:2]
            waist = gray_th[int(h * 0.55):int(h * 0.80), :]
            f.thermal_waist_region_heat = float(waist.mean() / 255.0) if waist.size > 0 else 0.0

        # ── Cross-sensor ────────────────────────────────────────────
        sensors_on = sum([
            1 if mmwave_result is not None else 0,
            1 if rgb_frame is not None and rgb_frame.size > 0 else 0,
            1 if thermal_frame is not None and thermal_frame.size > 0 else 0,
        ])
        f.any_sensor_active = float(sensors_on) / 3.0

        return f
