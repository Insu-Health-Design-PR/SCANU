"""Shared-memory latest-frame IPC (single producer, many readers)."""

from __future__ import annotations

import mmap
import os
import struct
from pathlib import Path

_HEADER_STRUCT = struct.Struct("<II")  # seq, size
_HEADER_SIZE = _HEADER_STRUCT.size
_DEFAULT_CAPACITY = 2 * 1024 * 1024  # 2 MiB


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class LiveFrameWriter:
    """Write latest JPEG bytes into a fixed-size mmap region."""

    def __init__(self, path: Path, capacity: int = _DEFAULT_CAPACITY) -> None:
        self.path = path.expanduser().resolve()
        self.capacity = int(max(64 * 1024, capacity))
        _ensure_parent(self.path)
        total = _HEADER_SIZE + self.capacity
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
        self._mm.write(_HEADER_STRUCT.pack(self._seq, 0))
        self._mm.seek(_HEADER_SIZE)
        self._mm.write(data)
        self._seq += 1
        self._mm.seek(0)
        self._mm.write(_HEADER_STRUCT.pack(self._seq, n))
        self._mm.flush(0, _HEADER_SIZE + n)
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
        self._total = _HEADER_SIZE + self.capacity

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
            for _ in range(2):
                self._mm.seek(0)
                seq1, size = _HEADER_STRUCT.unpack(self._mm.read(_HEADER_SIZE))
                if (seq1 & 1) != 0:
                    continue
                if size <= 0 or size > self.capacity:
                    return None
                self._mm.seek(_HEADER_SIZE)
                payload = self._mm.read(size)
                self._mm.seek(0)
                seq2, _size2 = _HEADER_STRUCT.unpack(self._mm.read(_HEADER_SIZE))
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

