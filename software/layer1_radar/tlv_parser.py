"""
TLV (Type-Length-Value) parser for radar frames.

Parses the TLV data structures from IWR6843 frames to extract:
- Detected points (x, y, z, doppler)
- Range profile
- Noise profile
- Statistics
- Side info (SNR, noise per point)
"""

import struct
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .radar_constants import TLVType, FRAME_HEADER_SIZE, POINT_SIZE, POINT_SIDE_INFO_SIZE
from .uart_source import FrameHeader

logger = logging.getLogger(__name__)


@dataclass
class DetectedPoint:
    """A single detected point from the radar."""
    x: float          # X position in meters
    y: float          # Y position in meters (range direction)
    z: float          # Z position in meters (elevation)
    doppler: float    # Velocity in m/s (positive = approaching)
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
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'doppler': self.doppler,
            'range': self.range,
            'azimuth_deg': self.azimuth_deg,
            'elevation_deg': self.elevation_deg,
            'snr': self.snr,
            'noise': self.noise,
        }


@dataclass
class ParsedFrame:
    """
    Completely parsed radar frame with all extracted data.
    """
    # Header info
    frame_number: int
    num_detected_obj: int
    num_tlvs: int
    timestamp_cycles: int
    
    # Detected objects
    points: List[DetectedPoint] = field(default_factory=list)
    
    # Range profile (1D array of energy vs range)
    range_profile: Optional[np.ndarray] = None
    
    # Noise profile
    noise_profile: Optional[np.ndarray] = None
    
    # Statistics
    stats: Dict[str, Any] = field(default_factory=dict)
    
    # Raw TLV data for debugging
    raw_tlvs: Dict[int, bytes] = field(default_factory=dict)
    
    def get_point_cloud(self) -> np.ndarray:
        """
        Get points as Nx4 numpy array [x, y, z, doppler].
        
        Returns:
            numpy array of shape (N, 4) or empty (0, 4) if no points
        """
        if not self.points:
            return np.zeros((0, 4), dtype=np.float32)
        
        return np.array(
            [[p.x, p.y, p.z, p.doppler] for p in self.points],
            dtype=np.float32
        )
    
    def get_point_cloud_with_snr(self) -> np.ndarray:
        """
        Get points as Nx6 numpy array [x, y, z, doppler, snr, noise].
        """
        if not self.points:
            return np.zeros((0, 6), dtype=np.float32)
        
        return np.array(
            [[p.x, p.y, p.z, p.doppler, p.snr, p.noise] for p in self.points],
            dtype=np.float32
        )
    
    def __str__(self) -> str:
        return (
            f"Frame #{self.frame_number}: "
            f"{len(self.points)} points, "
            f"range_profile={'yes' if self.range_profile is not None else 'no'}"
        )


class TLVParser:
    """
    Parses TLV frames from IWR6843 radar.
    
    Usage:
        parser = TLVParser()
        parsed = parser.parse(frame_bytes)
        
        for point in parsed.points:
            print(f"Object at ({point.x:.2f}, {point.y:.2f}, {point.z:.2f})")
    """
    
    def __init__(self):
        self._frames_parsed = 0
        self._parse_errors = 0
    
    def parse(self, frame: bytes) -> ParsedFrame:
        """
        Parse a complete frame.
        
        Args:
            frame: Raw frame bytes (including magic word and header)
            
        Returns:
            ParsedFrame with all extracted data
        """
        if len(frame) < FRAME_HEADER_SIZE:
            raise ValueError(f"Frame too short: {len(frame)} bytes")
        
        # Parse header
        header = FrameHeader.from_bytes(frame[:FRAME_HEADER_SIZE])
        
        # Initialize result
        result = ParsedFrame(
            frame_number=header.frame_number,
            num_detected_obj=header.num_detected_obj,
            num_tlvs=header.num_tlvs,
            timestamp_cycles=header.time_cpu_cycles,
        )
        
        # Parse TLVs
        offset = FRAME_HEADER_SIZE
        
        for _ in range(header.num_tlvs):
            if offset + 8 > len(frame):
                logger.warning(f"Frame truncated at TLV header (offset {offset})")
                break
            
            # TLV header: type (4 bytes) + length (4 bytes)
            tlv_type, tlv_length = struct.unpack('<II', frame[offset:offset+8])
            offset += 8
            
            if offset + tlv_length > len(frame):
                logger.warning(f"TLV {tlv_type} truncated (need {tlv_length}, have {len(frame)-offset})")
                break
            
            # Extract TLV data
            tlv_data = frame[offset:offset+tlv_length]
            offset += tlv_length
            
            # Store raw data
            result.raw_tlvs[tlv_type] = tlv_data
            
            # Parse based on type
            try:
                self._parse_tlv(tlv_type, tlv_data, result)
            except Exception as e:
                logger.warning(f"Error parsing TLV type {tlv_type}: {e}")
                self._parse_errors += 1
        
        self._frames_parsed += 1
        return result
    
    def _parse_tlv(self, tlv_type: int, data: bytes, result: ParsedFrame) -> None:
        """Parse a single TLV and update result."""
        
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
        """
        Parse detected points TLV.
        
        Each point: x(4) + y(4) + z(4) + doppler(4) = 16 bytes
        All values are float32.
        """
        num_points = len(data) // POINT_SIZE
        
        for i in range(num_points):
            offset = i * POINT_SIZE
            x, y, z, doppler = struct.unpack('<4f', data[offset:offset+POINT_SIZE])
            
            point = DetectedPoint(
                x=x,
                y=y,
                z=z,
                doppler=doppler
            )
            result.points.append(point)
        
        logger.debug(f"Parsed {num_points} detected points")
    
    def _parse_range_profile(self, data: bytes, result: ParsedFrame) -> None:
        """
        Parse range profile TLV.
        
        Array of uint16 values representing energy at each range bin.
        """
        num_bins = len(data) // 2
        result.range_profile = np.frombuffer(data, dtype=np.uint16).astype(np.float32)
        logger.debug(f"Parsed range profile: {num_bins} bins")
    
    def _parse_noise_profile(self, data: bytes, result: ParsedFrame) -> None:
        """
        Parse noise profile TLV.
        
        Array of uint16 values representing noise floor at each range bin.
        """
        num_bins = len(data) // 2
        result.noise_profile = np.frombuffer(data, dtype=np.uint16).astype(np.float32)
        logger.debug(f"Parsed noise profile: {num_bins} bins")
    
    def _parse_side_info(self, data: bytes, result: ParsedFrame) -> None:
        """
        Parse side info TLV (SNR and noise for each point).
        
        Each entry: snr(2) + noise(2) = 4 bytes
        Values are int16 in 0.1 dB units.
        """
        num_entries = len(data) // POINT_SIDE_INFO_SIZE
        
        for i, point in enumerate(result.points):
            if i >= num_entries:
                break
            
            offset = i * POINT_SIDE_INFO_SIZE
            snr_raw, noise_raw = struct.unpack('<2h', data[offset:offset+POINT_SIDE_INFO_SIZE])
            
            # Convert from 0.1 dB units to dB
            point.snr = snr_raw * 0.1
            point.noise = noise_raw * 0.1
        
        logger.debug(f"Parsed side info for {min(num_entries, len(result.points))} points")
    
    def _parse_stats(self, data: bytes, result: ParsedFrame) -> None:
        """
        Parse statistics TLV.
        
        Contains processing times and other diagnostic info.
        """
        if len(data) >= 24:
            stats = struct.unpack('<6I', data[:24])
            result.stats = {
                'interframe_proc_time': stats[0],
                'transmit_out_time': stats[1],
                'interframe_proc_margin': stats[2],
                'interchirp_proc_margin': stats[3],
                'active_frame_cpu_load': stats[4],
                'interframe_cpu_load': stats[5],
            }
        logger.debug(f"Parsed stats: {result.stats}")
    
    def get_stats(self) -> dict:
        """Get parser statistics."""
        return {
            'frames_parsed': self._frames_parsed,
            'parse_errors': self._parse_errors,
        }


# Convenience function
def parse_frame(frame: bytes) -> ParsedFrame:
    """
    Parse a single frame (convenience function).
    
    Args:
        frame: Raw frame bytes
        
    Returns:
        ParsedFrame with extracted data
    """
    parser = TLVParser()
    return parser.parse(frame)
