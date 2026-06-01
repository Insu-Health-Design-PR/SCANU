"""Temporal point-cloud tracker for weapon motion-pattern detection.
 
Tracks clusters across frames using DBSCAN + nearest-neighbour association and
detects weapon-characteristic motion patterns:
  - High doppler variance (hand tremor / micro-Doppler)
  - Rapid radial displacement (draw / swing)
  - Small spatial extent (< 0.4 m)  —  weapon-sized
  - Elevated RCS proxy  —  metallic return
  - Stable elevation  —  weapon held at consistent height
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from sklearn.cluster import DBSCAN


@dataclass
class TrackedCluster:
    cluster_id: int
    centroid: np.ndarray  # [x, y, z] in metres
    doppler_mean: float
    snr_mean: float
    spatial_extent: float  # metres
    point_count: int
    frames_alive: int
    frames_since_update: int
    velocity_xy: np.ndarray  # [vx, vy] from frame-to-frame delta
    doppler_variance: float
    rcs_proxy: float
    weapon_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "centroid": self.centroid.tolist(),
            "doppler_mean": self.doppler_mean,
            "snr_mean": self.snr_mean,
            "spatial_extent": self.spatial_extent,
            "point_count": self.point_count,
            "frames_alive": self.frames_alive,
            "velocity_xy": self.velocity_xy.tolist(),
            "doppler_variance": self.doppler_variance,
            "rcs_proxy": self.rcs_proxy,
            "weapon_confidence": self.weapon_confidence,
        }


@dataclass
class WeaponTracker:
    """Tracks clusters across frames and scores them for weapon likelihood."""

    max_distance_m: float = 1.0
    max_frames_missed: int = 5
    min_frames_for_track: int = 3

    weapon_size_min_m: float = 0.05
    weapon_size_max_m: float = 0.40
    weapon_doppler_var_min: float = 0.02
    weapon_snr_min_db: float = 6.0
    weapon_rcs_min: float = 1.0

    _clusters: deque[TrackedCluster] = field(default_factory=deque)
    _next_id: int = 0
    _history: deque[list[dict]] = field(default_factory=lambda: deque(maxlen=30))
    _score_log: deque[dict] = field(default_factory=lambda: deque(maxlen=100))

    def update(
        self,
        point_cloud: np.ndarray,
        *,
        cluster_radius_m: float = 0.75,
    ) -> list[TrackedCluster]:
        clusters_raw = self._cluster_points(point_cloud, cluster_radius_m)
        new_clusters = self._associate(clusters_raw)
        self._prune_stale()
        scores = self._score_weapon_likelihood(new_clusters)
        self._history.append([c.to_dict() for c in new_clusters if c.weapon_confidence > 0.1])
        return scores

    def recent_scores(self, limit: int = 20) -> list[dict]:
        return list(self._score_log)[-limit:]

    def top_threat(self) -> TrackedCluster | None:
        alive = [c for c in self._clusters if c.frames_since_update == 0]
        if not alive:
            return None
        return max(alive, key=lambda c: c.weapon_confidence)

    # ── clustering (DBSCAN) ─────────────────────────────────────────────

    def _cluster_points(
        self, cloud: np.ndarray, radius_m: float
    ) -> list[np.ndarray]:
        if cloud.size == 0 or cloud.shape[0] == 0:
            return []
        if cloud.shape[0] < 3:
            return [cloud]

        xy = cloud[:, :2]
        clustering = DBSCAN(eps=radius_m, min_samples=1).fit(xy)
        labels = clustering.labels_
        n_clusters = int(labels.max()) + 1 if labels.size > 0 else 0

        clusters: list[np.ndarray] = []
        for c in range(n_clusters):
            mask = labels == c
            clusters.append(cloud[mask])
        return clusters

    # ── association ─────────────────────────────────────────────────────

    def _associate(self, raw_clusters: list[np.ndarray]) -> list[TrackedCluster]:
        for existing in self._clusters:
            existing.frames_since_update += 1

        new_ids: list[int] = []
        for points in raw_clusters:
            centroid_xy = np.median(points[:, :2], axis=0) if points.shape[0] > 2 else np.mean(points[:, :2], axis=0)

            best_match: TrackedCluster | None = None
            best_dist = self.max_distance_m
            for existing in self._clusters:
                if existing.frames_since_update > 0:
                    continue
                d = float(np.linalg.norm(existing.centroid[:2] - centroid_xy))
                if d < best_dist:
                    best_dist = d
                    best_match = existing

            if best_match is not None:
                prev_centroid = best_match.centroid.copy()
                self._update_cluster(best_match, points)
                best_match.velocity_xy = (best_match.centroid[:2] - prev_centroid[:2]) * 1000.0
                best_match.frames_since_update = 0
                new_ids.append(best_match.cluster_id)
            else:
                new_cluster = self._create_cluster(points)
                self._clusters.append(new_cluster)
                new_ids.append(new_cluster.cluster_id)

        return [c for c in self._clusters if c.cluster_id in new_ids]

    def _update_cluster(self, cluster: TrackedCluster, points: np.ndarray) -> None:
        cluster.centroid = np.median(points[:, :3], axis=0) if points.shape[0] > 2 else np.mean(points[:, :3], axis=0)

        doppler = points[:, 3] if points.shape[1] >= 4 else np.array([])
        cluster.doppler_mean = float(np.mean(doppler)) if doppler.size > 0 else 0.0
        cluster.doppler_variance = float(np.var(doppler)) if doppler.size > 1 else 0.0

        snr = points[:, 4] if points.shape[1] >= 5 else np.array([])
        cluster.snr_mean = float(np.mean(snr)) if snr.size > 0 else 0.0

        if points.shape[0] >= 2:
            xy = points[:, :2]
            centroid_xy = cluster.centroid[:2]
            cluster.spatial_extent = float(np.max(np.sqrt(np.sum((xy - centroid_xy) ** 2, axis=1))))
        else:
            cluster.spatial_extent = 0.0

        ranges = np.sqrt(np.sum(points[:, :2] ** 2, axis=1))
        ranges = np.clip(ranges, 0.5, 10.0)
        if snr.size > 0:
            cluster.rcs_proxy = float(np.mean((10.0 ** (snr / 10.0)) * (ranges ** 4)))
        elif doppler.size > 0:
            cluster.rcs_proxy = float(np.mean(ranges ** 4)) * 0.1

        cluster.point_count = points.shape[0]
        cluster.frames_alive += 1

    def _create_cluster(self, points: np.ndarray) -> TrackedCluster:
        cid = self._next_id
        self._next_id += 1

        centroid = np.median(points[:, :3], axis=0) if points.shape[0] > 2 else np.mean(points[:, :3], axis=0)

        doppler = points[:, 3] if points.shape[1] >= 4 else np.array([])
        doppler_mean = float(np.mean(doppler)) if doppler.size > 0 else 0.0
        doppler_var = float(np.var(doppler)) if doppler.size > 1 else 0.0

        snr = points[:, 4] if points.shape[1] >= 5 else np.array([])
        snr_mean = float(np.mean(snr)) if snr.size > 0 else 0.0

        if points.shape[0] >= 2:
            xy = points[:, :2]
            c_xy = centroid[:2]
            extent = float(np.max(np.sqrt(np.sum((xy - c_xy) ** 2, axis=1))))
        else:
            extent = 0.0

        ranges = np.sqrt(np.sum(points[:, :2] ** 2, axis=1))
        ranges = np.clip(ranges, 0.5, 10.0)
        if snr.size > 0:
            rcs = float(np.mean((10.0 ** (snr / 10.0)) * (ranges ** 4)))
        elif doppler.size > 0:
            rcs = float(np.mean(ranges ** 4)) * 0.1
        else:
            rcs = 0.0

        return TrackedCluster(
            cluster_id=cid,
            centroid=centroid,
            doppler_mean=doppler_mean,
            snr_mean=snr_mean,
            spatial_extent=extent,
            point_count=points.shape[0],
            frames_alive=1,
            frames_since_update=0,
            velocity_xy=np.zeros(2, dtype=np.float32),
            doppler_variance=doppler_var,
            rcs_proxy=rcs,
            weapon_confidence=0.0,
        )

    def _prune_stale(self) -> None:
        to_remove = [c for c in self._clusters if c.frames_since_update > self.max_frames_missed]
        for c in to_remove:
            self._clusters.remove(c)

    # ── weapon-likelihood scoring ───────────────────────────────────────

    def _score_weapon_likelihood(
        self, clusters: list[TrackedCluster]
    ) -> list[TrackedCluster]:
        for cluster in clusters:
            if cluster.frames_alive < self.min_frames_for_track:
                cluster.weapon_confidence = 0.0
                continue

            scores: list[float] = []

            size = cluster.spatial_extent
            if self.weapon_size_min_m <= size <= self.weapon_size_max_m:
                scores.append(0.8)
            elif size < self.weapon_size_min_m * 2:
                scores.append(0.4)
            else:
                scores.append(0.0)

            dop_var = cluster.doppler_variance
            if dop_var >= self.weapon_doppler_var_min:
                scores.append(min(dop_var / 0.1, 0.8))
            else:
                scores.append(dop_var / self.weapon_doppler_var_min * 0.3)

            snr = cluster.snr_mean
            if snr >= self.weapon_snr_min_db:
                scores.append(min((snr - self.weapon_snr_min_db) / 10.0 + 0.5, 0.9))
            else:
                scores.append(snr / self.weapon_snr_min_db * 0.3)

            rcs = cluster.rcs_proxy
            if rcs >= self.weapon_rcs_min:
                scores.append(min(np.log10(rcs + 1) / 3.0, 0.7))
            else:
                scores.append(rcs / self.weapon_rcs_min * 0.2)

            vel_magnitude = float(np.linalg.norm(cluster.velocity_xy))
            if vel_magnitude > 0.1:
                scores.append(min(vel_magnitude / 2.0, 0.6))
            else:
                scores.append(0.1)

            cluster.weapon_confidence = float(np.clip(np.mean(scores), 0.0, 1.0))

            self._score_log.append({
                "cluster_id": cluster.cluster_id,
                "confidence": cluster.weapon_confidence,
                "size": cluster.spatial_extent,
                "doppler_var": cluster.doppler_variance,
                "snr": cluster.snr_mean,
                "rcs_proxy": cluster.rcs_proxy,
                "velocity": float(vel_magnitude),
                "frames_alive": cluster.frames_alive,
            })

        return clusters
