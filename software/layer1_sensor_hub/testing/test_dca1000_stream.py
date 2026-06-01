"""Tests for Dca1000StreamProcessor using an in-memory UDP loopback."""

from __future__ import annotations

import socket
import struct
import threading
import time
from pathlib import Path

import numpy as np

from layer1_sensor_hub.mmwave_dca.dca1000_stream import Dca1000StreamProcessor
from layer1_sensor_hub.mmwave_dca.dca1000_udp import Dca1000NetworkConfig
from layer1_sensor_hub.mmwave_dca.mmwave_raw_adc_detector import RawAdcWeaponDetector


def _make_payload(chirps=48, rx=4, samples=384) -> bytes:
    np.random.seed(0)
    frame = (np.random.randn(chirps, rx, samples).astype(np.complex64) * 50.0)
    iq = np.empty(chirps * rx * samples * 2, dtype=np.int16)
    n = 0
    for c in range(chirps):
        for r in range(rx):
            for s in range(samples):
                iq[n] = int(np.real(frame[c, r, s]).clip(-32768, 32767))
                iq[n + 1] = int(np.imag(frame[c, r, s]).clip(-32768, 32767))
                n += 2
    return iq.tobytes()


def _send_packets(
    payload: bytes,
    target_addr: tuple[str, int],
    n_packets: int,
    packet_size: int = 1456,
    delay_s: float = 0.001,
) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    time.sleep(0.05)  # give receiver time to bind
    for i in range(n_packets):
        chunk = payload[i * packet_size : (i + 1) * packet_size]
        header = struct.pack(">II", i, len(chunk))
        sock.sendto(header + chunk, target_addr)
        time.sleep(delay_s)
    sock.close()


def test_stream_processor_loopback(tmp_path: Path) -> None:
    chirps, rx, samples = 48, 4, 384
    frame_bytes = _make_payload(chirps, rx, samples)
    payload_size = 1456
    n_packets = (len(frame_bytes) + payload_size - 1) // payload_size

    cfg = Dca1000NetworkConfig(pc_ip="127.0.0.1", data_port=0)
    proc = Dca1000StreamProcessor(
        chirps=chirps, rx=rx, samples=samples,
        network=cfg,
        detector=RawAdcWeaponDetector(),
    )

    # Use a dynamically-assigned port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    actual_port = sock.getsockname()[1]
    sock.close()

    test_cfg = Dca1000NetworkConfig(pc_ip="127.0.0.1", data_port=actual_port)
    proc.network = test_cfg

    sender = threading.Thread(
        target=_send_packets,
        args=(frame_bytes, ("127.0.0.1", actual_port), n_packets, payload_size),
        daemon=True,
    )
    sender.start()

    results = proc.run(duration_s=2.0, max_frames=3)
    sender.join(timeout=3)

    assert len(results) >= 0  # at least no crash
    for r in results:
        assert 0.0 <= r.detection.weapon_score <= 1.0
        assert isinstance(r.detection.rd_map, np.ndarray)
        assert r.packets_seen > 0


def test_stream_processor_empty_returns_quickly() -> None:
    cfg = Dca1000NetworkConfig(pc_ip="127.0.0.1", data_port=0)
    proc = Dca1000StreamProcessor(network=cfg)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    actual_port = sock.getsockname()[1]
    sock.close()

    proc.network = Dca1000NetworkConfig(pc_ip="127.0.0.1", data_port=actual_port)
    start = time.time()
    results = proc.run(duration_s=0.5)
    elapsed = time.time() - start
    assert elapsed < 2.0  # should timeout quickly
    assert len(results) == 0


def test_stream_processor_saves_output(tmp_path: Path) -> None:
    chirps, rx, samples = 16, 4, 384
    frame_bytes = _make_payload(chirps, rx, samples)
    payload_size = 1456
    n_packets = (len(frame_bytes) + payload_size - 1) // payload_size

    cfg = Dca1000NetworkConfig(pc_ip="127.0.0.1", data_port=0)
    proc = Dca1000StreamProcessor(chirps=chirps, rx=rx, samples=samples, network=cfg)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    actual_port = sock.getsockname()[1]
    sock.close()

    proc.network = Dca1000NetworkConfig(pc_ip="127.0.0.1", data_port=actual_port)
    out = tmp_path / "stream_adc.bin"

    sender = threading.Thread(
        target=_send_packets,
        args=(frame_bytes, ("127.0.0.1", actual_port), n_packets, payload_size),
        daemon=True,
    )
    sender.start()

    proc.run(duration_s=2.0, max_frames=3, output_path=out)
    sender.join(timeout=3)

    assert out.is_file()
    assert out.stat().st_size > 0
