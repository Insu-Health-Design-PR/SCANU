"""
TLV (Type-Length-Value) parser for radar frames.

Parses the TLV data structures from IWR6843 frames to extract:
- Detected points (x, y, z, doppler)
- Range profile
- Noise profile
- Statistics
- Side info (SNR, noise per point)
"""

import logging
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .radar_constants import FRAME_HEADER_SIZE, POINT_SIDE_INFO_SIZE, POINT_SIZE, TLVType
from .uart_source import FrameHeader

logger = logging.getLogger(__name__)


@dataclass
class DetectedPoint:
    """A single detected point from the radar."""

    x: float  # X position in meters
    y: float  # Y position in meters (range direction)
    z: float  # Z position in meters (elevation)
    doppler: float  # Velocity in m/s (positive = approaching)
    snr: float = 0.0  # Signal-to-noise ratio (dB)
    noise: float = 0.0  # Noise level

    @property
    def range(self) -> float:
        """Calculate range (distance) from radar."""

        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    @property
    def azimuth_deg(self) -> float:
        """Calculate azimuth angle in degrees."""

        return np.degrees(np.arctan2(self.x, self.y))

    @property
    def elevation_deg(self) -> float:
        """Calculate elevation angle in degrees."""

        r_xy = np.sqrt(self.x**2 + self.y**2)
        return np.degrees(np.arctan2(self.z, r_xy))

    def to_dict(self) -> dict:
        """Convert to dictionary."""

        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "doppler": self.doppler,
            "range": self.range,
            "azimuth_deg": self.azimuth_deg,
            "elevation_deg": self.elevation_deg,
            "snr": self.snr,
            "noise": self.noise,
        }


@dataclass
class ParsedFrame:
    """Completely parsed radar frame with all extracted data."""

    frame_number: int
    num_detected_obj: int
    num_tlvs: int
    timestamp_cycles: int

    points: List[DetectedPoint] = field(default_factory=list)
    range_profile: Optional[np.ndarray] = None
    noise_profile: Optional[np.ndarray] = None
    stats: Dict[str, Any] = field(default_factory=dict)
    raw_tlvs: Dict[int, bytes] = field(default_factory=dict)

    def get_point_cloud(self) -> np.ndarray:
        """Get points as Nx4 numpy array [x, y, z, doppler]."""

        if not self.points:
            return np.zeros((0, 4), dtype=np.float32)

        return np.array([[p.x, p.y, p.z, p.doppler] for p in self.points], dtype=np.float32)

    def get_point_cloud_with_snr(self) -> np.ndarray:
        """Get points as Nx6 numpy array [x, y, z, doppler, snr, noise]."""

        if not self.points:
            return np.zeros((0, 6), dtype=np.float32)

        return np.array([[p.x, p.y, p.z, p.doppler, p.snr, p.noise] for p in self.points], dtype=np.float32)

    def __str__(self) -> str:
        return (
            f"Frame #{self.frame_number}: "
            f"{len(self.points)} points, "
            f"range_profile={'yes' if self.range_profile is not None else 'no'}"
        )


class TLVParser:
    """Parses TLV frames from IWR6843 radar."""

    def __init__(self):
        self._frames_parsed = 0
        self._parse_errors = 0

    def parse(self, frame: bytes) -> ParsedFrame:
        """Parse a complete frame."""

        if len(frame) < FRAME_HEADER_SIZE:
            raise ValueError(f"Frame too short: {len(frame)} bytes")

        header = FrameHeader.from_bytes(frame[:FRAME_HEADER_SIZE])

        result = ParsedFrame(
            frame_number=header.frame_number,
            num_detected_obj=header.num_detected_obj,
            num_tlvs=header.num_tlvs,
            timestamp_cycles=header.time_cpu_cycles,
        )

        offset = FRAME_HEADER_SIZE

        for _ in range(header.num_tlvs):
            if offset + 8 > len(frame):
                logger.warning(f"Frame truncated at TLV header (offset {offset})")
                break

            tlv_type, tlv_length = struct.unpack("<II", frame[offset : offset + 8])
            offset += 8

            payload_length = self._resolve_tlv_payload_length(
                tlv_type=tlv_type,
                tlv_length=tlv_length,
                remaining=len(frame) - offset,
            )
            if payload_length is None:
                logger.warning(
                    "TLV %s invalid/truncated (raw_len=%s, remaining=%s)",
                    tlv_type,
                    tlv_length,
                    len(frame) - offset,
                )
                break

            tlv_data = frame[offset : offset + payload_length]
            offset += payload_length

            result.raw_tlvs[tlv_type] = tlv_data

            try:
                self._parse_tlv(tlv_type, tlv_data, result)
            except Exception as e:
                logger.warning(f"Error parsing TLV type {tlv_type}: {e}")
                self._parse_errors += 1

        self._frames_parsed += 1
        return result

    @staticmethod
    def _resolve_tlv_payload_length(tlv_type: int, tlv_length: int, remaining: int) -> int | None:
        """
        Return TLV payload length from raw TLV length field.

        Different TI parser examples in the wild treat `tlv_length` as either:
        1) payload-only length
        2) TLV total length including 8-byte TL header
        This resolver accepts both to avoid frame misalignment.
        """
        if tlv_length <= 0:
            return None

        # Prefer payload-only interpretation when sane.
        if tlv_length <= remaining:
            payload_len = tlv_length
            if payload_len > 0:
                return payload_len

        # Fallback: `tlv_length` includes the 8-byte TL header.
        if tlv_length >= 8:
            payload_len = tlv_length - 8
            if 0 < payload_len <= remaining:
                logger.debug(
                    "TLV %s using inclusive-length mode (raw=%s -> payload=%s)",
                    tlv_type,
                    tlv_length,
                    payload_len,
                )
                return payload_len

        return None

    def _parse_tlv(self, tlv_type: int, data: bytes, result: ParsedFrame) -> None:
        if tlv_type == TLVType.DETECTED_POINTS:
            self._parse_detected_points(data, result)
        elif tlv_type == TLVType.RANGE_PROFILE:
            self._parse_range_profile(data, result)
        elif tlv_type == TLVType.NOISE_PROFILE:
            self._parse_noise_profile(data, result)
        elif tlv_type == TLVType.DETECTED_POINTS_SIDE_INFO:
            self._parse_side_info(data, result)
        elif tlv_type == TLVType.STATS:
            self._parse_stats(data, result)
        else:
            logger.debug(f"Unhandled TLV type {tlv_type} ({len(data)} bytes)")

    def _parse_detected_points(self, data: bytes, result: ParsedFrame) -> None:
        num_points = len(data) // POINT_SIZE

        for i in range(num_points):
            offset = i * POINT_SIZE
            x, y, z, doppler = struct.unpack("<4f", data[offset : offset + POINT_SIZE])
            result.points.append(DetectedPoint(x=x, y=y, z=z, doppler=doppler))

        logger.debug(f"Parsed {num_points} detected points")

    def _parse_range_profile(self, data: bytes, result: ParsedFrame) -> None:
        result.range_profile = np.frombuffer(data, dtype=np.uint16).astype(np.float32)

    def _parse_noise_profile(self, data: bytes, result: ParsedFrame) -> None:
        result.noise_profile = np.frombuffer(data, dtype=np.uint16).astype(np.float32)

    def _parse_side_info(self, data: bytes, result: ParsedFrame) -> None:
        num_entries = len(data) // POINT_SIDE_INFO_SIZE

        for i in range(min(num_entries, len(result.points))):
            offset = i * POINT_SIDE_INFO_SIZE
            snr, noise = struct.unpack("<2H", data[offset : offset + POINT_SIDE_INFO_SIZE])
            result.points[i].snr = snr / 10.0
            result.points[i].noise = float(noise)

    def _parse_stats(self, data: bytes, result: ParsedFrame) -> None:
        if len(data) < 24:
            return
        inter_frame_proc_time, transmit_out_time, inter_frame_proc_margin, inter_chirp_proc_margin, active_frame_cpu_load, inter_frame_cpu_load = struct.unpack(
            "<6I", data[:24]
        )
        result.stats.update(
            {
                "inter_frame_proc_time": inter_frame_proc_time,
                "transmit_out_time": transmit_out_time,
                "inter_frame_proc_margin": inter_frame_proc_margin,
                "inter_chirp_proc_margin": inter_chirp_proc_margin,
                "active_frame_cpu_load": active_frame_cpu_load,
                "inter_frame_cpu_load": inter_frame_cpu_load,
            }
        )


def parse_frame(frame: bytes) -> ParsedFrame:
    """Parse a single frame (convenience function)."""

    return TLVParser().parse(frame)
