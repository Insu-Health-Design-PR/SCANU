"""Tests for KalmanFilterTracker."""

from __future__ import annotations

import numpy as np

from layer5_fusion.kalman_tracker import KalmanFilterTracker, FusedTrack


def test_kalman_predict_update_cycle() -> None:
    kf = KalmanFilterTracker(dt=0.05, process_noise=0.01, measurement_noise=0.1)
    track = FusedTrack(
        track_id=1,
        x=1.0, y=2.0, vx=0.0, vy=0.0,
        age=0, last_update_ms=0.0,
        x_est=np.array([[1.0], [2.0], [0.0], [0.0]], dtype=np.float32),
    )
    kf.update_track(track, np.array([1.5, 2.5]))
    # state should move toward measurement
    assert abs(track.x - 1.5) < 0.6
    assert abs(track.y - 2.5) < 0.6


def test_kalman_associate_and_update() -> None:
    kf = KalmanFilterTracker(dt=0.05, max_age=10, process_noise=0.1, measurement_noise=0.5)
    measurements = [(1.0, 2.0, "mmwave"), (3.0, 4.0, "thermal")]
    tracks = kf.associate_and_update(measurements, 1000.0)
    assert len(tracks) == 2
    assert tracks[0].track_id == 0
    assert tracks[1].track_id == 1
    assert tracks[0].sensor_source == "mmwave"
    assert tracks[1].sensor_source == "thermal"


def test_kalman_association_reuses_tracks() -> None:
    kf = KalmanFilterTracker(dt=0.05, max_age=10)
    m1 = [(1.0, 2.0, "mmwave")]
    t1 = kf.associate_and_update(m1, 1000.0)
    assert len(t1) == 1
    assert t1[0].track_id == 0

    # same measurement should associate to same track
    m2 = [(1.1, 2.1, "mmwave")]
    t2 = kf.associate_and_update(m2, 1100.0)
    assert len(t2) == 1
    assert t2[0].track_id == 0  # same track, not new


def test_kalman_far_measurement_creates_new_track() -> None:
    kf = KalmanFilterTracker(dt=0.05, max_age=10, process_noise=0.1, measurement_noise=0.5)
    m1 = [(1.0, 2.0, "mmwave")]
    kf.associate_and_update(m1, 1000.0)
    # far away -> new track
    m2 = [(10.0, 10.0, "mmwave")]
    t2 = kf.associate_and_update(m2, 1100.0)
    assert len(t2) == 1
    assert t2[0].track_id == 1


def test_kalman_predict_all_ages_tracks() -> None:
    kf = KalmanFilterTracker(dt=0.05, max_age=3)
    kf.associate_and_update([(1.0, 2.0, "mmwave")], 1000.0)
    for _ in range(4):  # age goes 1,2,3,4 -> max_age=3 means age > 3 is stale
        kf.predict_all()
    assert len(kf.get_active_tracks()) == 0  # aged out


def test_kalman_get_active_tracks() -> None:
    kf = KalmanFilterTracker(dt=0.05, max_age=10)
    kf.associate_and_update([(1.0, 2.0, "mmwave")], 1000.0)
    assert len(kf.get_active_tracks()) == 1

    kf.predict_all()
    kf.predict_all()
    assert len(kf.get_active_tracks()) == 1  # age < 5

    for _ in range(5):
        kf.predict_all()
    assert len(kf.get_active_tracks()) == 0


def test_kalman_clear() -> None:
    kf = KalmanFilterTracker()
    kf.associate_and_update([(1.0, 2.0, "mmwave")], 1000.0)
    assert len(kf.get_active_tracks()) == 1
    kf.clear()
    assert len(kf.get_active_tracks()) == 0


def test_fused_track_to_dict() -> None:
    track = FusedTrack(
        track_id=1, x=1.0, y=2.0, vx=0.1, vy=0.2,
        age=3, last_update_ms=1000.0, sensor_source="thermal",
    )
    d = track.to_dict()
    assert d["track_id"] == 1
    assert d["sensor_source"] == "thermal"
    assert d["age"] == 3
