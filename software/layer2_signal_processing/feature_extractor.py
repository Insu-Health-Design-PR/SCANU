"""Feature extraction helpers for Layer 2 heatmaps — weapon-detection edition."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .signal_processor import ProcessedFrame


@dataclass(frozen=True)
class HeatmapFeatures:
    """Heatmap projections and summary vector derived from one processed frame."""

    frame_number: int
    timestamp_ms: float
    range_heatmap: np.ndarray
    doppler_heatmap: np.ndarray

    vector: np.ndarray  # full feature vector

    micro_doppler_bandwidth: float
    doppler_centroid: float
    doppler_spread: float
    azimuth_static_peak: float
    point_count: int
    mean_snr: float
    max_snr: float
    spatial_extent_m: float
    rcs_proxy_mean: float


class FeatureExtractor:
    """Builds deterministic heatmap + weapon-relevant features from a range-doppler map."""

    _VECTOR_FIELDS = [
        "mean_rd",
        "std_rd",
        "max_rd",
        "min_rd",
        "point_count",
        "micro_doppler_bandwidth",
        "doppler_centroid",
        "doppler_spread",
        "azimuth_static_peak",
        "mean_snr",
        "max_snr",
        "spatial_extent_m",
        "rcs_proxy_mean",
        "rd_energy_ratio",
    ]

    def extract(self, processed: ProcessedFrame) -> HeatmapFeatures:
        rd = np.asarray(processed.range_doppler, dtype=np.float32)
        if rd.ndim != 2:
            raise ValueError("ProcessedFrame.range_doppler must be 2D")

        range_heatmap = np.sum(rd, axis=0, dtype=np.float32)
        doppler_heatmap = np.sum(rd, axis=1, dtype=np.float32)

        pc = processed.point_cloud
        point_count = int(pc.shape[0])

        snr_values = pc[:, 4] if pc.shape[1] >= 5 else np.array([], dtype=np.float32)
        mean_snr = float(np.mean(snr_values)) if snr_values.size > 0 else 0.0
        max_snr = float(np.max(snr_values)) if snr_values.size > 0 else 0.0

        spatial_extent_m = 0.0
        if pc.shape[0] >= 2:
            xy = pc[:, :2]
            centroid = np.mean(xy, axis=0)
            distances = np.sqrt(np.sum((xy - centroid) ** 2, axis=1))
            spatial_extent_m = float(np.max(distances))

        rcs_proxy_mean = 0.0
        if snr_values.size > 0:
            ranges = np.sqrt(np.sum(pc[:, :2] ** 2, axis=1))
            ranges = np.clip(ranges, 0.5, 10.0)
            rcs_proxy = (10.0 ** (snr_values / 10.0)) * (ranges ** 4)
            rcs_proxy_mean = float(np.mean(rcs_proxy))

        total_energy = float(np.sum(rd))
        rd_energy_ratio = 0.0
        if total_energy > 0 and point_count > 0:
            brightest = np.sort(rd.ravel())[-max(point_count, 1):]
            rd_energy_ratio = float(np.sum(brightest)) / total_energy

        vector = np.array(
            [
                float(np.mean(rd)),
                float(np.std(rd)),
                float(np.max(rd)),
                float(np.min(rd)),
                float(point_count),
                processed.micro_doppler_bandwidth,
                processed.doppler_centroid,
                processed.doppler_spread,
                processed.azimuth_static_peak,
                mean_snr,
                max_snr,
                spatial_extent_m,
                rcs_proxy_mean,
                rd_energy_ratio,
            ],
            dtype=np.float32,
        )

        return HeatmapFeatures(
            frame_number=processed.frame_number,
            timestamp_ms=processed.timestamp_ms,
            range_heatmap=range_heatmap,
            doppler_heatmap=doppler_heatmap,
            vector=vector,
            micro_doppler_bandwidth=processed.micro_doppler_bandwidth,
            doppler_centroid=processed.doppler_centroid,
            doppler_spread=processed.doppler_spread,
            azimuth_static_peak=processed.azimuth_static_peak,
            point_count=point_count,
            mean_snr=mean_snr,
            max_snr=max_snr,
            spatial_extent_m=spatial_extent_m,
            rcs_proxy_mean=rcs_proxy_mean,
        )

    @classmethod
    def vector_field_names(cls) -> list[str]:
        return list(cls._VECTOR_FIELDS)
