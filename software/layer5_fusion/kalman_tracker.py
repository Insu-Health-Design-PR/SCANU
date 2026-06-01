"""Per-track Kalman filter for mmWave + thermal sensor fusion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FusedTrack:
    track_id: int
    x: float
    y: float
    vx: float
    vy: float
    age: int
    last_update_ms: float
    x_est: np.ndarray = field(default_factory=lambda: np.zeros((4, 1), dtype=np.float32))
    p_est: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float32) * 100.0)
    sensor_source: str = "mmwave"

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "age": self.age,
            "sensor_source": self.sensor_source,
        }


class KalmanFilterTracker:

    def __init__(self, dt: float = 0.05, process_noise: float = 0.1, measurement_noise: float = 0.5, max_age: int = 30):
        self.dt = dt
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float32)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=np.float32)
        self.Q = np.eye(4, dtype=np.float32) * process_noise
        self.R = np.eye(2, dtype=np.float32) * measurement_noise
        self._tracks: dict[int, FusedTrack] = {}
        self._next_id = 0
        self._max_age = max_age
        self._association_distance_m = 1.5

    def predict_all(self) -> None:
        to_remove: list[int] = []
        for tid, track in self._tracks.items():
            track.x_est = self.F @ track.x_est
            track.p_est = self.F @ track.p_est @ self.F.T + self.Q
            track.age += 1
            if track.age > self._max_age:
                to_remove.append(tid)
        for tid in to_remove:
            del self._tracks[tid]

    def update_track(self, track: FusedTrack, z: np.ndarray, sensor_source: str = "mmwave") -> None:
        y = z.reshape(2, 1) - self.H @ track.x_est
        S = self.H @ track.p_est @ self.H.T + self.R
        K = track.p_est @ self.H.T @ np.linalg.inv(S)
        track.x_est = track.x_est + K @ y
        track.p_est = (np.eye(4, dtype=np.float32) - K @ self.H) @ track.p_est
        track.x = float(track.x_est[0, 0])
        track.y = float(track.x_est[1, 0])
        track.vx = float(track.x_est[2, 0])
        track.vy = float(track.x_est[3, 0])
        track.age = 0
        track.last_update_ms = 0.0
        track.sensor_source = sensor_source

    def associate_and_update(self, measurements: list[tuple[float, float, str]], timestamp_ms: float) -> list[FusedTrack]:
        updated: list[FusedTrack] = []
        assigned_measurements: set[int] = set()
        assigned_tracks: set[int] = set()

        for tid, track in self._tracks.items():
            best_idx = -1
            best_dist = self._association_distance_m
            for i, (mx, my, src) in enumerate(measurements):
                if i in assigned_measurements:
                    continue
                d = np.linalg.norm(track.x_est[:2] - np.array([[mx], [my]]))
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            if best_idx >= 0:
                mx, my, src = measurements[best_idx]
                self.update_track(track, np.array([mx, my]), src)
                assigned_measurements.add(best_idx)
                assigned_tracks.add(tid)
                updated.append(track)

        for i, (mx, my, src) in enumerate(measurements):
            if i in assigned_measurements:
                continue
            z = np.array([[mx], [my]])
            x_est = np.vstack([z, np.zeros((2, 1), dtype=np.float32)])
            new_track = FusedTrack(
                track_id=self._next_id,
                x=mx, y=my, vx=0.0, vy=0.0,
                age=0, last_update_ms=timestamp_ms,
                x_est=x_est,
                sensor_source=src,
            )
            self._tracks[self._next_id] = new_track
            updated.append(new_track)
            self._next_id += 1

        return updated

    def get_active_tracks(self) -> list[FusedTrack]:
        return [t for t in self._tracks.values() if t.age < 5]

    def clear(self) -> None:
        self._tracks.clear()
