"""Shared-memory latest-frame IPC (single producer, many readers)."""

from __future__ import annotations

import mmap
import os
import struct
from pathlib import Path

_JPEG_HEADER_STRUCT = struct.Struct("<II")  # seq, size
_JPEG_HEADER_SIZE = _JPEG_HEADER_STRUCT.size
_BGR_HEADER_STRUCT = struct.Struct("<IIIII")  # seq, size, height, width, channels
_BGR_HEADER_SIZE = _BGR_HEADER_STRUCT.size
_DEFAULT_CAPACITY = 2 * 1024 * 1024  # 2 MiB
_DEFAULT_BGR_CAPACITY = 8 * 1024 * 1024  # 8 MiB (enough for 1080p BGR)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class LiveFrameWriter:
    """Write latest JPEG bytes into a fixed-size mmap region."""

    def __init__(self, path: Path, capacity: int = _DEFAULT_CAPACITY) -> None:
        self.path = path.expanduser().resolve()
        self.capacity = int(max(64 * 1024, capacity))
        _ensure_parent(self.path)
        total = _JPEG_HEADER_SIZE + self.capacity
        with open(self.path, "wb") as f:
            f.truncate(total)
        self._fp = open(self.path, "r+b", buffering=0)
        self._mm = mmap.mmap(self._fp.fileno(), total, access=mmap.ACCESS_WRITE)
        self._seq = 0

    def write(self, payload: bytes) -> bool:
        data = bytes(payload or b"")
        if not data:
            return False
        n = len(data)
        if n > self.capacity:
            return False
        # seqlock-style update: odd=in-progress, even=stable.
        self._seq += 1
        self._mm.seek(0)
        self._mm.write(_JPEG_HEADER_STRUCT.pack(self._seq, 0))
        self._mm.seek(_JPEG_HEADER_SIZE)
        self._mm.write(data)
        self._seq += 1
        self._mm.seek(0)
        self._mm.write(_JPEG_HEADER_STRUCT.pack(self._seq, n))
        self._mm.flush(0, _JPEG_HEADER_SIZE + n)
        return True

    def close(self) -> None:
        try:
            self._mm.close()
        finally:
            self._fp.close()


class LiveFrameReader:
    """Read latest stable JPEG bytes from mmap region."""

    def __init__(self, path: Path, capacity: int = _DEFAULT_CAPACITY) -> None:
        self.path = path.expanduser().resolve()
        self.capacity = int(max(64 * 1024, capacity))
        self._fp = None
        self._mm = None
        self._total = _JPEG_HEADER_SIZE + self.capacity

    def _open_if_needed(self) -> bool:
        if self._mm is not None:
            return True
        if not self.path.is_file():
            return False
        try:
            self._fp = open(self.path, "r+b", buffering=0)
            self._mm = mmap.mmap(self._fp.fileno(), self._total, access=mmap.ACCESS_READ)
            return True
        except OSError:
            self.close()
            return False

    def read_latest(self) -> bytes | None:
        if not self._open_if_needed():
            return None
        assert self._mm is not None
        try:
            for _ in range(12):
                self._mm.seek(0)
                seq1, size = _JPEG_HEADER_STRUCT.unpack(self._mm.read(_JPEG_HEADER_SIZE))
                if (seq1 & 1) != 0:
                    continue
                if size <= 0 or size > self.capacity:
                    return None
                self._mm.seek(_JPEG_HEADER_SIZE)
                payload = self._mm.read(size)
                self._mm.seek(0)
                seq2, _size2 = _JPEG_HEADER_STRUCT.unpack(self._mm.read(_JPEG_HEADER_SIZE))
                if seq1 == seq2 and (seq2 & 1) == 0:
                    return payload if payload else None
            return None
        except (ValueError, OSError):
            self.close()
            return None

    def close(self) -> None:
        if self._mm is not None:
            try:
                self._mm.close()
            except OSError:
                pass
            self._mm = None
        if self._fp is not None:
            try:
                self._fp.close()
            except OSError:
                pass
            self._fp = None


class LiveBgrFrameWriter:
    """Write latest raw BGR frame bytes into a fixed-size mmap region."""

    def __init__(self, path: Path, capacity: int = _DEFAULT_BGR_CAPACITY) -> None:
        self.path = path.expanduser().resolve()
        self.capacity = int(max(256 * 1024, capacity))
        _ensure_parent(self.path)
        total = _BGR_HEADER_SIZE + self.capacity
        with open(self.path, "wb") as f:
            f.truncate(total)
        self._fp = open(self.path, "r+b", buffering=0)
        self._mm = mmap.mmap(self._fp.fileno(), total, access=mmap.ACCESS_WRITE)
        self._seq = 0

    def write(self, payload: bytes, *, height: int, width: int, channels: int) -> bool:
        data = bytes(payload or b"")
        if not data:
            return False
        n = len(data)
        if n > self.capacity:
            return False
        if height <= 0 or width <= 0 or channels <= 0:
            return False
        self._seq += 1
        self._mm.seek(0)
        self._mm.write(_BGR_HEADER_STRUCT.pack(self._seq, 0, 0, 0, 0))
        self._mm.seek(_BGR_HEADER_SIZE)
        self._mm.write(data)
        self._seq += 1
        self._mm.seek(0)
        self._mm.write(_BGR_HEADER_STRUCT.pack(self._seq, n, int(height), int(width), int(channels)))
        self._mm.flush(0, _BGR_HEADER_SIZE + n)
        return True

    def close(self) -> None:
        try:
            self._mm.close()
        finally:
            self._fp.close()


class LiveBgrFrameReader:
    """Read latest stable raw BGR frame from mmap region."""

    def __init__(self, path: Path, capacity: int = _DEFAULT_BGR_CAPACITY) -> None:
        self.path = path.expanduser().resolve()
        self.capacity = int(max(256 * 1024, capacity))
        self._fp = None
        self._mm = None
        self._total = _BGR_HEADER_SIZE + self.capacity

    def _open_if_needed(self) -> bool:
        if self._mm is not None:
            return True
        if not self.path.is_file():
            return False
        try:
            self._fp = open(self.path, "r+b", buffering=0)
            self._mm = mmap.mmap(self._fp.fileno(), self._total, access=mmap.ACCESS_READ)
            return True
        except OSError:
            self.close()
            return False

    def read_latest(self) -> tuple[bytes, int, int, int] | None:
        if not self._open_if_needed():
            return None
        assert self._mm is not None
        try:
            for _ in range(12):
                self._mm.seek(0)
                seq1, size, height, width, channels = _BGR_HEADER_STRUCT.unpack(
                    self._mm.read(_BGR_HEADER_SIZE)
                )
                if (seq1 & 1) != 0:
                    continue
                if size <= 0 or size > self.capacity:
                    return None
                if height <= 0 or width <= 0 or channels <= 0:
                    return None
                self._mm.seek(_BGR_HEADER_SIZE)
                payload = self._mm.read(size)
                self._mm.seek(0)
                seq2, size2, height2, width2, channels2 = _BGR_HEADER_STRUCT.unpack(
                    self._mm.read(_BGR_HEADER_SIZE)
                )
                if (
                    seq1 == seq2
                    and (seq2 & 1) == 0
                    and size == size2
                    and height == height2
                    and width == width2
                    and channels == channels2
                ):
                    return payload, int(height), int(width), int(channels)
            return None
        except (ValueError, OSError):
            self.close()
            return None

    def close(self) -> None:
        if self._mm is not None:
            try:
                self._mm.close()
            except OSError:
                pass
            self._mm = None
        if self._fp is not None:
            try:
                self._fp.close()
            except OSError:
                pass
            self._fp = None

