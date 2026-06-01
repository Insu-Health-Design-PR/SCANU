"""Streaming UDP DCA1000 processor — detect weapons in real-time per packet.

Processes ADC data incrementally as UDP packets arrive, without waiting
for the full capture to complete. Each packet contributes to a rolling
buffer of complete frames; when a frame is ready it is passed through
RawAdcWeaponDetector and the results are yielded immediately.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generator, Optional

import numpy as np

from .dca1000_udp import Dca1000NetworkConfig
from .mmwave_raw_adc_detector import MmwaveDetectionResult, RawAdcWeaponDetector


@dataclass
class StreamResult:
    frame_number: int
    detection: MmwaveDetectionResult
    elapsed_s: float
    packets_seen: int
    payload_bytes: int


class Dca1000StreamProcessor:
    """Stream DCA1000 UDP packets and yield per-frame detection results.

    Usage::

        processor = Dca1000StreamProcessor(
            chirps=48, rx=4, samples=384,
            on_frame_ready=lambda r: print(f\"Frame {r.frame_number}: score={r.detection.weapon_score:.3f}\"),
        )
        processor.run(duration_s=5.0)
    """

    def __init__(
        self,
        chirps: int = 48,
        rx: int = 4,
        samples: int = 384,
        network: Optional[Dca1000NetworkConfig] = None,
        detector: Optional[RawAdcWeaponDetector] = None,
        on_frame_ready: Optional[Callable[[StreamResult], None]] = None,
    ) -> None:
        self.chirps = chirps
        self.rx = rx
        self.samples = samples
        self.frame_size = chirps * rx * samples * 2 * 2  # int16 * I+Q
        self.network = network or Dca1000NetworkConfig()
        self.detector = detector or RawAdcWeaponDetector()
        self.on_frame_ready = on_frame_ready

    def run(
        self,
        *,
        duration_s: float = 5.0,
        max_frames: int = 0,
        on_ready: Optional[Callable[[], None]] = None,
        output_path: Optional[str | Path] = None,
    ) -> list[StreamResult]:
        results: list[StreamResult] = []
        buf = bytearray()
        packets = 0
        payload_bytes = 0
        frame_count = 0
        start = time.monotonic()
        out_fh: Any = None

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            out_fh = p.open("wb")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.network.pc_ip, self.network.data_port))
                sock.settimeout(self.network.socket_timeout_s)

                if on_ready is not None:
                    on_ready()

                while True:
                    if (time.monotonic() - start) >= duration_s:
                        break
                    if max_frames and frame_count >= max_frames:
                        break

                    try:
                        packet, _addr = sock.recvfrom(self.network.packet_size + 64)
                    except socket.timeout:
                        break

                    payload = packet[10:] if len(packet) > 10 else packet
                    buf.extend(payload)
                    if out_fh is not None:
                        out_fh.write(payload)
                    packets += 1
                    payload_bytes += len(payload)

                    while len(buf) >= self.frame_size:
                        frame_bytes = bytes(buf[:self.frame_size])
                        buf = buf[self.frame_size:]
                        frame = self._bytes_to_frame(frame_bytes)
                        if frame is None:
                            continue

                        detection = self.detector.detect(frame, frame_number=frame_count)
                        elapsed = time.monotonic() - start
                        result = StreamResult(
                            frame_number=frame_count,
                            detection=detection,
                            elapsed_s=elapsed,
                            packets_seen=packets,
                            payload_bytes=payload_bytes,
                        )
                        results.append(result)
                        frame_count += 1
                        if self.on_frame_ready:
                            self.on_frame_ready(result)
        finally:
            if out_fh is not None:
                out_fh.close()

        return results

    def _bytes_to_frame(self, raw: bytes) -> Optional[np.ndarray]:
        expected = self.chirps * self.rx * self.samples * 2 * 2
        if len(raw) < expected:
            return None
        data = np.frombuffer(raw[:expected], dtype=np.int16)
        data = data.astype(np.float32)
        # TI interleaved: I0,I1,I2,I3,Q0,Q1,Q2,Q3 -> complex
        complex_data = np.empty(data.size // 2, dtype=np.complex64)
        complex_data[0::2] = data[0::4] + 1j * data[2::4]
        complex_data[1::2] = data[1::4] + 1j * data[3::4]
        return complex_data.reshape(self.chirps, self.rx, self.samples)
