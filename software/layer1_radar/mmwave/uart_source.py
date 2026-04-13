"""
UART data source for reading TLV frames from radar.

Reads raw bytes from the data port and assembles complete frames
using the magic word for synchronization.
"""

import logging
import struct
from dataclasses import dataclass
from typing import Generator, Optional

from .radar_constants import FRAME_HEADER_SIZE, MAGIC_WORD
from .serial_manager import SerialManager

logger = logging.getLogger(__name__)


@dataclass
class FrameHeader:
    """
    Parsed TLV frame header.

    The header is 40 bytes total:
    - 8 bytes: Magic word
    - 32 bytes: Header fields
    """

    magic_word: bytes
    version: int
    total_packet_length: int
    platform: int
    frame_number: int
    time_cpu_cycles: int
    num_detected_obj: int
    num_tlvs: int
    subframe_number: int

    @classmethod
    def from_bytes(cls, data: bytes) -> "FrameHeader":
        """Parse header from raw bytes (must be at least 40 bytes)."""

        if len(data) < FRAME_HEADER_SIZE:
            raise ValueError(f"Header requires {FRAME_HEADER_SIZE} bytes, got {len(data)}")

        # Magic word is first 8 bytes
        magic = data[0:8]

        # Parse remaining fields (little-endian 32-bit unsigned integers)
        fields = struct.unpack("<8I", data[8:40])

        return cls(
            magic_word=magic,
            version=fields[0],
            total_packet_length=fields[1],
            platform=fields[2],
            frame_number=fields[3],
            time_cpu_cycles=fields[4],
            num_detected_obj=fields[5],
            num_tlvs=fields[6],
            subframe_number=fields[7],
        )

    def __str__(self) -> str:
        return (
            f"Frame #{self.frame_number}: "
            f"{self.num_detected_obj} objects, "
            f"{self.num_tlvs} TLVs, "
            f"{self.total_packet_length} bytes"
        )


class UARTSource:
    """
    Reads and yields complete TLV frames from radar data port.

    Handles:
    - Byte stream buffering
    - Magic word synchronization
    - Frame boundary detection
    - Partial frame handling
    """

    def __init__(self, serial_manager: SerialManager, buffer_size: int = 65536):
        self.serial = serial_manager
        self._buffer = bytearray()
        self._buffer_size = buffer_size
        self._frames_read = 0
        self._bytes_read = 0
        self._sync_errors = 0

    def _find_magic_word(self) -> int:
        """Find magic word in buffer."""

        try:
            return self._buffer.index(MAGIC_WORD)
        except ValueError:
            return -1

    def _read_available(self) -> int:
        """Read all available bytes from data port into buffer."""

        if not self.serial.data_port or not self.serial.data_port.is_open:
            raise RuntimeError("Data port not connected")

        available = self.serial.data_port.in_waiting
        if available > 0:
            # Limit read to prevent buffer overflow
            max_read = self._buffer_size - len(self._buffer)
            to_read = min(available, max_read)

            if to_read > 0:
                data = self.serial.data_port.read(to_read)
                self._buffer.extend(data)
                self._bytes_read += len(data)
                return len(data)

        return 0

    def read_frame(self, timeout_ms: int = 200) -> Optional[bytes]:
        """Read a single complete frame from the radar."""

        import time

        start_time = time.time()
        timeout_sec = timeout_ms / 1000.0

        while (time.time() - start_time) < timeout_sec:
            # Read any available data
            self._read_available()

            # Find magic word
            magic_idx = self._find_magic_word()

            if magic_idx == -1:
                # Keep only last 7 bytes (partial magic word possible)
                if len(self._buffer) > 7:
                    discarded = len(self._buffer) - 7
                    self._buffer = self._buffer[-7:]
                    if discarded > 100:
                        logger.debug(f"Discarded {discarded} bytes (no magic word)")
                continue

            # Discard data before magic word
            if magic_idx > 0:
                self._sync_errors += 1
                logger.debug(f"Sync: discarded {magic_idx} bytes before magic word")
                self._buffer = self._buffer[magic_idx:]

            # Check if we have enough for header
            if len(self._buffer) < FRAME_HEADER_SIZE:
                continue

            # Parse header to get total length
            try:
                header = FrameHeader.from_bytes(bytes(self._buffer[:FRAME_HEADER_SIZE]))
            except Exception as e:
                logger.warning(f"Header parse error: {e}")
                self._buffer = self._buffer[8:]
                continue

            # Sanity check packet length
            if header.total_packet_length < FRAME_HEADER_SIZE:
                logger.warning(f"Invalid packet length: {header.total_packet_length}")
                self._buffer = self._buffer[8:]
                continue

            if header.total_packet_length > self._buffer_size:
                logger.warning(f"Packet too large: {header.total_packet_length}")
                self._buffer = self._buffer[8:]
                continue

            # Check if we have complete frame
            if len(self._buffer) < header.total_packet_length:
                continue

            frame = bytes(self._buffer[: header.total_packet_length])
            self._buffer = self._buffer[header.total_packet_length :]

            self._frames_read += 1
            logger.debug(f"Read frame #{header.frame_number}: {len(frame)} bytes")

            return frame

        return None

    def stream_frames(self, max_frames: int = 0) -> Generator[bytes, None, None]:
        """Generator that yields frames as they arrive."""

        count = 0
        while max_frames == 0 or count < max_frames:
            frame = self.read_frame()
            if frame:
                count += 1
                yield frame

    def get_stats(self) -> dict:
        """Get source statistics."""

        return {
            "frames_read": self._frames_read,
            "bytes_read": self._bytes_read,
            "sync_errors": self._sync_errors,
            "buffer_size": len(self._buffer),
        }

    def clear_buffer(self) -> int:
        """Clear the internal buffer."""

        cleared = len(self._buffer)
        self._buffer.clear()
        return cleared

