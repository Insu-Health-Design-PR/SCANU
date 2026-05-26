"""Raw ADC weapon detector — zone-tuned CFAR, features, point cloud.

Uses primitives from adc_reader.py and adds weapon-optimised CFAR with
zone-specific coherence analysis tuned for concealed firearms on the body.

Typical usage::

    detector = RawAdcWeaponDetector()
    for frame_idx in range(adc.shape[0]):
        result = detector.detect(adc[frame_idx])
        print(f"Frame {frame_idx}: weapon_score={result.weapon_score:.3f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .adc_reader import coherence_factor, compute_mti, range_doppler_map, range_fft


@dataclass(frozen=True)
class MmweaponCfarParams:
    """2D CFAR parameters optimised for compact reflector detection."""

    range_guard: int = 2
    range_train: int = 4
    doppler_guard: int = 1
    doppler_train: int = 3
    threshold_scale: float = 8.0
    noise_floor_offset_db: float = 3.0
    max_points: int = 64


@dataclass(frozen=True)
class WeaponZoneParams:
    """Range-bin zone where a concealed weapon is expected.

    When a person is detected (via MTI motion) the zone is placed relative
    to the motion peak; otherwise a static fallback zone is used.

    Static fallback covers 1.2–1.9 m (bins 90–150), tuned for a person
    standing ~1 m from the radar with the weapon at waist height.
    """

    static_start: int = 90
    static_end: int = 150
    motion_offset_start: int = -60
    motion_offset_end: int = -15


@dataclass
class MmwaveDetectionResult:
    """Output of one frame processed by RawAdcWeaponDetector."""

    frame_number: int
    weapon_score: float
    rd_map: np.ndarray
    cfar_mask: np.ndarray
    point_cloud: Optional[np.ndarray]
    features: dict[str, float]


class RawAdcWeaponDetector:
    """Process raw ADC frames and produce weapon scores + point clouds.

    Steps per frame:
    1. Range-Doppler map
    2. MTI filtering (clutter suppression)
    3. Weapon-tuned 2D CFAR
    4. Zone-specific coherence analysis
    5. Feature extraction (zone-focused)
    6. Composite weapon score
    7. 3D point cloud
    """

    def __init__(
        self,
        cfar: MmweaponCfarParams = MmweaponCfarParams(),
        zone: WeaponZoneParams = WeaponZoneParams(),
        mti_alpha: float = 0.8,
    ) -> None:
        self.cfar = cfar
        self.zone = zone
        self.mti_alpha = mti_alpha

    def detect(self, frame: np.ndarray, frame_number: int = 0) -> MmwaveDetectionResult:
        chirps, rx, samples = frame.shape

        rd = range_doppler_map(frame, window=True)

        mti_frame = compute_mti(frame, alpha=self.mti_alpha)
        mti_rd = range_doppler_map(mti_frame, window=True)

        cfar_mask = self._cfar_2d(mti_rd)

        # Point cloud CFAR: use raw RD on person range only (bins 30-200)
        rd_person = rd[:, 30:200]
        cfar_person = np.zeros_like(rd, dtype=bool)
        cfar_person[:, 30:200] = self._cfar_2d(rd_person)

        coh = coherence_factor(frame)
        pstab = self._phase_stability(frame)

        features = self._extract_features(rd, mti_rd, cfar_mask, coh, pstab, frame)

        weapon_score = self._compute_weapon_score(features)

        cloud = self._build_point_cloud(rd, cfar_person, frame, rd) if np.any(cfar_person) else None

        return MmwaveDetectionResult(
            frame_number=frame_number,
            weapon_score=weapon_score,
            rd_map=rd,
            cfar_mask=cfar_mask,
            point_cloud=cloud,
            features=features,
        )

    def _cfar_2d(self, rd_map: np.ndarray) -> np.ndarray:
        n_doppler, n_range = rd_map.shape
        mask = np.zeros_like(rd_map, dtype=bool)

        g_r, t_r = self.cfar.range_guard, self.cfar.range_train
        g_d, t_d = self.cfar.doppler_guard, self.cfar.doppler_train

        for d in range(g_d + t_d, n_doppler - g_d - t_d):
            for r in range(g_r + t_r, n_range - g_r - t_r):
                cell = rd_map[d, r]

                guard = rd_map[
                    d - g_d : d + g_d + 1,
                    r - g_r : r + g_r + 1,
                ]
                train = rd_map[
                    d - g_d - t_d : d + g_d + t_d + 1,
                    r - g_r - t_r : r + g_r + t_r + 1,
                ]
                noise = train.copy()
                noise[
                    g_d : g_d + 2 * g_d + 1,
                    g_r : g_r + 2 * g_r + 1,
                ] = np.nan
                noise_floor = np.nanmean(noise)
                if np.isnan(noise_floor):
                    continue

                threshold = noise_floor + self.cfar.threshold_scale + self.cfar.noise_floor_offset_db
                if cell > threshold:
                    mask[d, r] = True

        return mask

    def _extract_features(
        self,
        rd: np.ndarray,
        mti_rd: np.ndarray,
        cfar_mask: np.ndarray,
        coherence: np.ndarray,
        phase_stability: np.ndarray,
        frame: np.ndarray,
    ) -> dict[str, float]:
        zs = self.zone.static_start
        ze = self.zone.static_end

        mti_range_prof = mti_rd.sum(axis=0)
        motion_peak_bin = int(np.argmax(mti_range_prof[30:200])) + 30
        motion_energy = float(mti_range_prof[motion_peak_bin])

        peak_idx = np.unravel_index(np.argmax(rd), rd.shape)
        peak_range_bin = int(peak_idx[1])
        peak_doppler_bin = int(peak_idx[0])
        peak_mag = float(rd[peak_idx])
        mean_rd = float(rd.mean())
        std_rd = float(rd.std())

        mti_energy = float(np.sum(mti_rd ** 2))
        mti_peak = float(mti_rd.max())

        n_detections = int(np.sum(cfar_mask))
        if n_detections > 0:
            cfar_mean_mag = float(rd[cfar_mask].mean())
            cfar_max_mag = float(rd[cfar_mask].max())
        else:
            cfar_mean_mag = -100.0
            cfar_max_mag = -100.0

        mean_coherence = float(coherence.mean())
        max_coherence = float(coherence.max())
        coherence_peak_bin = int(np.argmax(coherence))

        zone_coh = coherence[zs:ze]
        zone_coherence_max = float(zone_coh.max()) if len(zone_coh) > 0 else 0.0
        zone_coherence_mean = float(zone_coh.mean()) if len(zone_coh) > 0 else 0.0

        bg_indices = np.setdiff1d(np.arange(20, 200), np.arange(zs, ze))
        bg_coherence_mean = float(coherence[bg_indices].mean()) if len(bg_indices) > 0 else 0.0
        coherence_contrast = zone_coherence_max / max(bg_coherence_mean, 1e-6)

        zone_pstab = phase_stability[zs:ze]
        zone_phase_stability = float(zone_pstab.max()) if len(zone_pstab) > 0 else 0.0

        bg_pstab = phase_stability[20:200]
        bg_indices2 = np.setdiff1d(np.arange(len(bg_pstab)), np.arange(zs, ze) - 20)
        bg_phase_stability = float(bg_pstab[bg_indices2].mean()) if len(bg_indices2) > 0 else 0.0
        pstab_contrast = zone_phase_stability / max(bg_phase_stability, 1e-6)

        zone_rd = rd[:, zs:ze]
        zone_energy = float(zone_rd.sum())
        total_energy = float(rd.sum())
        zone_energy_ratio = zone_energy / max(total_energy, 1e-6)

        doppler_profile = np.sum(rd, axis=1)
        doppler_above_noise = doppler_profile > (doppler_profile.mean() + std_rd)
        micro_doppler_spread = float(np.sum(doppler_above_noise))

        detections_in_zone = 0
        range_spread = 0.0
        if n_detections > 0:
            det_rows, det_cols = np.where(cfar_mask)
            in_zone = (det_cols >= zs) & (det_cols < ze)
            detections_in_zone = int(np.sum(in_zone))
            if np.any(in_zone):
                zone_det_cols = det_cols[in_zone]
                range_spread = float(zone_det_cols.max() - zone_det_cols.min())
            else:
                range_spread = float(det_cols.max() - det_cols.min())

        return {
            "peak_range_bin": peak_range_bin,
            "peak_doppler_bin": peak_doppler_bin,
            "peak_mag_db": peak_mag,
            "mean_rd_db": mean_rd,
            "std_rd_db": std_rd,
            "mti_energy": mti_energy,
            "mti_peak_db": mti_peak,
            "n_cfar_detections": n_detections,
            "n_cfar_detections_zone": detections_in_zone,
            "cfar_mean_mag_db": cfar_mean_mag,
            "cfar_max_mag_db": cfar_max_mag,
            "mean_coherence": mean_coherence,
            "max_coherence": max_coherence,
            "coherence_peak_bin": coherence_peak_bin,
            "motion_peak_bin": motion_peak_bin,
            "motion_energy": motion_energy,
            "zone_start": zs,
            "zone_end": ze,
            "zone_coherence_max": zone_coherence_max,
            "zone_coherence_mean": zone_coherence_mean,
            "coherence_contrast": coherence_contrast,
            "zone_phase_stability": zone_phase_stability,
            "pstab_contrast": pstab_contrast,
            "zone_energy_ratio": zone_energy_ratio,
            "micro_doppler_spread_bins": micro_doppler_spread,
            "range_spread_bins": range_spread,
        }

    def _compute_weapon_score(self, f: dict[str, float]) -> float:
        zc = f["zone_coherence_max"]
        zone_coh_score = min(1.0, max(0.0, (zc - 0.08) / 0.10))

        cc = f["coherence_contrast"]
        contrast_score = min(1.0, max(0.0, (cc - 0.60) / 0.60))

        zer = f["zone_energy_ratio"]
        energy_ratio_score = min(1.0, max(0.0, (zer - 0.140) / 0.015))

        score = (
            0.45 * zone_coh_score
            + 0.40 * contrast_score
            + 0.15 * energy_ratio_score
        )
        return float(np.clip(score, 0.0, 1.0))

    @staticmethod
    def _phase_stability(frame: np.ndarray) -> np.ndarray:
        rfft = np.fft.fft(frame, axis=-1)
        rfft_sum = np.sum(rfft, axis=1)
        phase = np.angle(rfft_sum)
        mean_cos = np.mean(np.cos(phase), axis=0)
        mean_sin = np.mean(np.sin(phase), axis=0)
        return np.sqrt(mean_cos ** 2 + mean_sin ** 2)

    @staticmethod
    def _unwrap_phase(ph: np.ndarray) -> np.ndarray:
        diff = np.diff(ph)
        correction = np.where(diff > np.pi, -2 * np.pi, 0)
        correction = np.where(diff < -np.pi, 2 * np.pi, correction)
        return np.cumsum(np.concatenate([[ph[0]], correction]))

    def _estimate_angle(
        self, frame: np.ndarray, range_bin: int, doppler_bin: int
    ) -> float:
        chirps, rx, samples = frame.shape
        cell = frame[:, :, range_bin]
        phase = np.angle(cell[doppler_bin, :])

        if len(phase) >= 2:
            phase_unwrapped = RawAdcWeaponDetector._unwrap_phase(phase)
            coeffs = np.polyfit(np.arange(rx), phase_unwrapped, 1)
            phase_slope = coeffs[0]
            angle_rad = np.arcsin(np.clip(phase_slope / np.pi, -1.0, 1.0))
            return float(angle_rad)
        return 0.0

    def _build_point_cloud(
        self,
        mti_rd: np.ndarray,
        cfar_mask: np.ndarray,
        frame: np.ndarray,
        rd: np.ndarray,
    ) -> np.ndarray:
        det_indices = np.argwhere(cfar_mask)
        if len(det_indices) == 0:
            return np.empty((0, 5), dtype=np.float32)

        zs, ze = self.zone.static_start, self.zone.static_end
        in_zone = (det_indices[:, 1] >= zs) & (det_indices[:, 1] < ze)

        strengths = rd[cfar_mask]
        if len(strengths) > self.cfar.max_points:
            top_k = np.argpartition(strengths, -self.cfar.max_points)[-self.cfar.max_points:]
            det_indices = det_indices[top_k]
            strengths = strengths[top_k]
            in_zone = in_zone[top_k]

        points = []
        for (d_bin, r_bin), snr, wz in zip(det_indices, strengths, in_zone):
            angle = self._estimate_angle(frame, int(r_bin), int(d_bin))
            points.append([float(r_bin), float(d_bin), angle, float(snr), float(wz)])

        return np.array(points, dtype=np.float32)
